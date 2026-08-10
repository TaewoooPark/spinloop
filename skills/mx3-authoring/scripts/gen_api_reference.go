// gen_api_reference generates the authoritative mx3 API index from a live
// mumax3 engine, so the reference can never drift from the binary in use.
//
// It must run from the root of a mumax3-ultrafast checkout, because it links
// against the engine and asks it what it actually registered:
//
//	cp gen_api_reference.go <mumax3-repo>/cmd/genapi/main.go
//	cd <mumax3-repo> && go run ./cmd/genapi -out .../references/api-index.md
//
// Modes:
//
//	-out FILE     write the index (default: stdout)
//	-check FILE   compare against FILE, exit 1 if they differ (drift detection)
//
// Note: engine registration happens in package init(), but cuda.Init() must
// still run first — the same order cmd/mumax3 uses before -vet.
package main

import (
	"flag"
	"fmt"
	"os"
	"reflect"
	"sort"
	"strings"

	"github.com/mumax/3/cuda"
	"github.com/mumax/3/engine"
)

var (
	flagOut   = flag.String("out", "", "write index to this file (default stdout)")
	flagCheck = flag.String("check", "", "compare against this file, exit 1 on drift")
)

// methodsHidden are reflect methods that exist on engine types but are not
// part of the scripting surface: plumbing the script layer never calls.
var methodsHidden = map[string]bool{
	"Eval": true, "EvalTo": true, "Slice": true, "Mesh": true,
	"NComp": true, "Type": true, "InputType": true, "MSlice": true,
	"Gpu": true, "Buffer": true, "Quantity": true, "String": true,
	"SetValue": true, "HostCopy": true, "HostArray": true, "HostList": true,
	"SetRegionFn": true, "AddTo": true, "Fix": true, "Child": true,
}

type entry struct {
	kind string // "func" | "var" | "meth"
	name string
	sig  string
	doc  string
}

func main() {
	flag.Parse()
	cuda.Init(0)

	entries := collect()
	out := render(entries)

	if *flagCheck != "" {
		have, err := os.ReadFile(*flagCheck)
		if err != nil {
			fmt.Fprintln(os.Stderr, "check: cannot read", *flagCheck, "-", err)
			os.Exit(1)
		}
		if strings.TrimSpace(string(have)) != strings.TrimSpace(out) {
			fmt.Fprintln(os.Stderr, "DRIFT:", *flagCheck, "no longer matches the engine.")
			fmt.Fprintln(os.Stderr, "Regenerate with: go run ./cmd/genapi -out", *flagCheck)
			os.Exit(1)
		}
		fmt.Println("api-index.md matches the engine.")
		return
	}

	if *flagOut != "" {
		if err := os.WriteFile(*flagOut, []byte(out), 0o644); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		fmt.Fprintln(os.Stderr, "wrote", *flagOut, "-", len(entries), "entries")
		return
	}
	fmt.Print(out)
}

func collect() []entry {
	ident := engine.World.Identifiers
	docs := engine.World.Doc

	// Canonical (cased) name per lowercased key. World stores identifiers
	// lowercased; Doc keeps the declared casing, which is what users read.
	cased := make(map[string]string, len(docs))
	for k := range docs {
		cased[strings.ToLower(k)] = k
	}

	var out []entry
	typesSeen := map[reflect.Type]bool{}
	// queue of types whose methods we still owe: seeded from identifier types,
	// then extended with function *return* types. Shape and Config are Go func
	// types reached only as return values -- miss them and the 15 geometry and
	// state composition methods vanish from the index.
	var queue []reflect.Type

	names := make([]string, 0, len(ident))
	for k := range ident {
		names = append(names, k)
	}
	sort.Strings(names)

	for _, k := range names {
		e := ident[k]
		t := e.Type()
		if t == nil {
			continue
		}
		name := cased[k]
		if name == "" {
			name = k
		}
		doc := docs[name]

		if t.Kind() == reflect.Func {
			out = append(out, entry{"func", name, funcSig(t), doc})
			for i := 0; i < t.NumOut(); i++ {
				queue = append(queue, t.Out(i))
			}
			continue
		}
		out = append(out, entry{"var", name, shortType(t), doc})
		queue = append(queue, t)
	}

	// Walk the queue. Methods can return further scriptable types
	// (Shape.Add -> Shape), so keep going until it drains.
	for len(queue) > 0 {
		t := queue[0]
		queue = queue[1:]
		if t == nil || typesSeen[t] {
			continue
		}
		typesSeen[t] = true

		recv := shortType(t)
		if !scriptableReceiver(recv) {
			continue
		}
		for i := 0; i < t.NumMethod(); i++ {
			m := t.Method(i)
			// Methods suffixed "Go" are deliberately hidden from the script
			// layer (script.GoExclusiveMethodSuffix).
			if strings.HasSuffix(m.Name, "Go") || methodsHidden[m.Name] {
				continue
			}
			if m.PkgPath != "" { // unexported
				continue
			}
			out = append(out, entry{"meth", recv + "." + m.Name, methodSig(m.Type), ""})
			for j := 1; j < m.Type.NumOut()+1 && j <= m.Type.NumOut(); j++ {
				queue = append(queue, m.Type.Out(j-1))
			}
		}
	}

	sort.Slice(out, func(i, j int) bool {
		if out[i].kind != out[j].kind {
			return kindRank(out[i].kind) < kindRank(out[j].kind)
		}
		return strings.ToLower(out[i].name) < strings.ToLower(out[j].name)
	})
	return out
}

func kindRank(k string) int {
	switch k {
	case "func":
		return 0
	case "var":
		return 1
	default:
		return 2
	}
}

// scriptableReceiver filters out plumbing types users never name in a script.
func scriptableReceiver(name string) bool {
	switch name {
	case "float64", "int", "bool", "string", "Time", "Duration":
		return false
	}
	return true
}

func funcSig(t reflect.Type) string {
	var in []string
	for i := 0; i < t.NumIn(); i++ {
		in = append(in, shortType(t.In(i)))
	}
	if t.IsVariadic() && len(in) > 0 {
		in[len(in)-1] = "..." + strings.TrimPrefix(in[len(in)-1], "[]")
	}
	sig := "(" + strings.Join(in, ", ") + ")"
	if t.NumOut() > 0 {
		var outs []string
		for i := 0; i < t.NumOut(); i++ {
			outs = append(outs, shortType(t.Out(i)))
		}
		sig += " " + strings.Join(outs, ", ")
	}
	return sig
}

// methodSig renders a method signature without its receiver argument.
func methodSig(t reflect.Type) string {
	var in []string
	for i := 1; i < t.NumIn(); i++ { // skip receiver
		in = append(in, shortType(t.In(i)))
	}
	if t.IsVariadic() && len(in) > 0 {
		in[len(in)-1] = "..." + strings.TrimPrefix(in[len(in)-1], "[]")
	}
	sig := "(" + strings.Join(in, ", ") + ")"
	if t.NumOut() > 0 {
		var outs []string
		for i := 0; i < t.NumOut(); i++ {
			outs = append(outs, shortType(t.Out(i)))
		}
		sig += " " + strings.Join(outs, ", ")
	}
	return sig
}

// shortType strips package qualifiers and pointers: script users write
// `Msat`, not `*engine.RegionwiseScalar`.
func shortType(t reflect.Type) string {
	if t == nil {
		return "void"
	}
	s := t.String()
	s = strings.TrimPrefix(s, "*")
	for _, p := range []string{"engine.", "data.", "script.", "interface {}"} {
		if p == "interface {}" {
			s = strings.ReplaceAll(s, p, "any")
			continue
		}
		s = strings.ReplaceAll(s, p, "")
	}
	return s
}

func render(entries []entry) string {
	var b strings.Builder
	nf, nv, nm := 0, 0, 0
	for _, e := range entries {
		switch e.kind {
		case "func":
			nf++
		case "var":
			nv++
		default:
			nm++
		}
	}

	b.WriteString("# mx3 API index\n\n")
	b.WriteString("GENERATED FILE - do not edit by hand.\n")
	b.WriteString("Regenerate with `scripts/gen_api_reference.go`; verify with its `-check` mode.\n\n")
	b.WriteString("    ENGINE: " + engine.UNAME + "\n\n")
	b.WriteString(fmt.Sprintf("Extracted from a live engine: **%d functions, %d variables, %d methods**.\n\n",
		nf, nv, nm))
	b.WriteString("This index describes the engine named above. If the `mumax3` on your\n")
	b.WriteString("PATH is a different build, it may not accept everything listed here -\n")
	b.WriteString("`scripts/preflight.sh` probes the actual binary and reports the gap.\n\n")
	b.WriteString("Identifiers are **case-insensitive** (`setgridsize` == `SetGridSize`).\n")
	b.WriteString("If a name is not in this file, it does not exist. Do not guess.\n\n")

	sections := []struct{ kind, title, note string }{
		{"func", "Functions", "Call as `Name(args)`."},
		{"var", "Variables", "Assign with `Name = value`; read where a quantity is accepted."},
		{"meth", "Methods", "Call on a value of the receiver type: `Msat.SetRegion(1, 800e3)`, `Circle(1e-7).Add(...)`."},
	}
	for _, s := range sections {
		b.WriteString("## " + s.title + "\n\n" + s.note + "\n\n```\n")
		for _, e := range entries {
			if e.kind != s.kind {
				continue
			}
			line := fmt.Sprintf("%-34s %-46s", e.name, e.sig)
			line = strings.TrimRight(line, " ")
			if e.doc != "" {
				line = fmt.Sprintf("%-34s %-46s  %s", e.name, e.sig, oneLine(e.doc))
			}
			b.WriteString(line + "\n")
		}
		b.WriteString("```\n\n")
	}
	return b.String()
}

func oneLine(s string) string {
	s = strings.ReplaceAll(s, "<br>", " ")
	s = strings.ReplaceAll(s, "\n", " ")
	s = strings.Join(strings.Fields(s), " ")
	return s
}
