# The mx3 language

mx3 is parsed by Go's own `go/parser` and then compiled by a small interpreter
in `script/`. That is why it looks like Go. It is not Go: the compiler accepts a
deliberately tiny subset and rejects everything else.

Everything below was read out of `script/*.go`, not recalled.

## Statements — the complete list

`script/stmt.go` dispatches on exactly seven AST node types:

| Allowed | Example |
|---|---|
| `AssignStmt` | `Msat = 800e3`, `n := 128` |
| `ExprStmt` | `Run(1e-9)` |
| `IfStmt` | `if x > 0 { ... } else { ... }` |
| `ForStmt` | `for i := 0; i < 10; i++ { ... }` |
| `IncDecStmt` | `i++`, `i--` |
| `BlockStmt` | `{ ... }` |
| `EmptyStmt` | `;` |

Anything else is a compile error. In particular **these do not exist in mx3**:

```go
func helper(x float64) float64 { ... }   // no function declarations
for i := range xs { ... }                // not allowed: RangeStmt
break / continue / return                // no
switch x { ... }                         // no
[]float64{1,2,3}   map[string]int{}      // no slices, no maps
import "math"                            // no imports (math is preloaded)
```

Verified:

```
$ mumax3 -vet bad.mx3
bad.mx3 : script line 2: for i := range 5 {...}: not allowed: RangeStmt
bad.mx3 : script line 3:6: expected '(', found myHelper:
```

### There are no user-defined functions

This is the constraint that most often forces a rewrite. To repeat a
calculation, you either inline it, put it in a `for` body, or split the work
into several files and run them as a batch:

```bash
mumax3 -j 3 sweep_*.mx3
```

## Expressions

`script/expr.go` accepts: `Ident`, `BasicLit`, `BinaryExpr`, `UnaryExpr`,
`CallExpr`, `ParenExpr`, `IndexExpr`.

Note what is missing: **`SelectorExpr` is not an expression.** `a.b` cannot be
read as a value. Selectors are only compiled as *method calls*, in
`script/call.go`:

```go
Msat.SetRegion(1, 800e3)     // ok - method call
m.Average()                  // ok - method call
x := someQuantity.Name       // not valid - selector as a value
```

## Identifiers are case-insensitive

`script/world.go` lowercases every name on declaration and on lookup:

```go
w.Identifiers[strings.ToLower(key)] = value
```

So all of these are the same identifier:

```go
SetGridSize(128, 32, 1)
setgridsize(128, 32, 1)
SETGRIDSIZE(128, 32, 1)
```

The engine's own test suite writes lowercase throughout. Prefer the canonical
casing shown in `api-index.md` for readability, but never assume a name is
undefined because its casing differs.

## Methods ending in `Go` are hidden

`script/selector.go` skips any method whose name ends in the
`GoExclusiveMethodSuffix` (`"Go"`), and any method starting with a lowercase
letter. Those exist for the Go API only and are invisible from a script.

## Closures capture only `t`

`script/world.go` declares the time variable through a special `TVar` wrapper,
described in the source as a "hack for fixing the closure caveat: declare the
time variable, the only variable closures close over."

This is what makes time-dependent excitations work:

```go
B_ext = vector(0, 0, 0.01 * sin(2*pi*1e9*t))
```

A closure over any *other* variable captures its value at declaration time, not
at evaluation time. Do not rely on it.

## Assignment forms

```go
n := 128        // declare (Go short form)
Msat = 800e3    // assign to an engine variable
alpha = 0.02
i++             // increment
```

Assigning to a read-only quantity is rejected at compile time — `ROnly`
identifiers such as `t`, `step`, `maxTorque` can be read but not set.

## Comments

`//` to end of line and `/* ... */` blocks, as in Go.

## What `-vet` does and does not check

`cmd/mumax3/vet.go` calls `engine.World.Compile()` per file inside a fresh
scope. That gives you:

- parse errors (unsupported syntax)
- undefined identifiers
- wrong argument counts
- assignment to read-only quantities

It does **not** give you:

- type sanity — `SetGridSize(128e-9, 32, 1)` compiles, truncates to 0, and dies
  at runtime
- any physics, units, or ordering beyond name resolution
- anything that only fails when the world is built (bad region index, empty
  geometry, missing OVF file)

`-vet` also calls `cuda.Init()` before compiling, so it needs a working GPU
backend. It is not a CPU-only linter.
