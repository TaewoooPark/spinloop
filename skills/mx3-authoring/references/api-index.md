# mx3 API index

GENERATED FILE - do not edit by hand.
Regenerate with `scripts/gen_api_reference.go`; verify with its `-check` mode.

    ENGINE: mumax 3.12 [darwin_arm64 go1.26.5(gc) Metal-3]

Extracted from a live engine: **186 functions, 156 variables, 185 methods**.

This index describes the engine named above. If the `mumax3` on your
PATH is a different build, it may not accept everything listed here -
`scripts/preflight.sh` probes the actual binary and reports the gap.

Identifiers are **case-insensitive** (`setgridsize` == `SetGridSize`).
If a name is not in this file, it does not exist. Do not guess.

## Functions

Call as `Name(args)`.

```
abs                                (float64) float64
acos                               (float64) float64
acosh                              (float64) float64
Add                                (Quantity, Quantity) Quantity                   Add two quantities
AddEdensTerm                       (Quantity)                                      Add an expression to Edens.
AddFieldTerm                       (Quantity)                                      Add an expression to B_eff.
Antivortex                         (int, int) Config                               Antivortex magnetization with given circulation and core polarization
asin                               (float64) float64
asinh                              (float64) float64
atan                               (float64) float64
atan2                              (float64, float64) float64
atanh                              (float64) float64
AutoSave                           (Quantity, float64)                             Auto save space-dependent quantity every period (s).
AutoSnapshot                       (Quantity, float64)                             Auto save image of quantity every period (s).
BlochSkyrmion                      (int, int) Config                               Bloch skyrmion magnetization with given chirality and core polarization
cbrt                               (float64) float64
ceil                               (float64) float64
Cell                               (int, int, int) Shape                           Single cell with given integer index (i, j, k)
CellIndices                        () Slice                                        4D slice containing the index of each cell as (ix, iy, iz).
Circle                             (float64) Shape                                 2D Circle with diameter in meter
ClearPostSteps                     ()                                              Clear the postStep array, which contains functions that are executed after each solver step. This includes running averages, centering routines to track skyrmions and domain walls etc.
Cone                               (float64, float64) Shape                        3D Cone with diameter and height in meter. The base is at z=0. If the height is positive, the tip points in the +z direction.
Conical                            (Vector, Vector, float64) Config                Conical state for given wave vector, cone direction, and cone angle
Const                              (float64) Quantity                              Constant, uniform number
ConstVector                        (float64, float64, float64) Quantity            Constant, uniform vector
cos                                (float64) float64
cosh                               (float64) float64
Crop                               (Quantity, int, int, int, int, int, int) cropped  Crops a quantity to cell ranges [x1,x2[, [y1,y2[, [z1,z2[
CropLayer                          (Quantity, int) cropped                         Crops a quantity to a single layer
CropRegion                         (Quantity, int) cropped                         Crops a quantity to a region
CropX                              (Quantity, int, int) cropped                    Crops a quantity to cell ranges [x1,x2[
CropY                              (Quantity, int, int) cropped                    Crops a quantity to cell ranges [y1,y2[
CropZ                              (Quantity, int, int) cropped                    Crops a quantity to cell ranges [z1,z2[
Cross                              (Quantity, Quantity) Quantity                   Cross product of two vector quantities
Cuboid                             (float64, float64, float64) Shape               Cuboid with sides in meter
CurrentMag                         () Config                                       Returns the current magnetization as a Config. E.g. CurrentMag().Add(0.1, RandomMagSeed(123)) will return a Config with the current magnetization plus some noise.
CustomQuantity                     (Slice) Quantity                                Creates an arbitrary custom Quantity from a user provided (scalar or vector) slice. The slice should match the simulation grid size, and can be created with NewScalarMask or NewVectorMask, or loaded in via Loadfile. Variations in slice values are not restricted to the 256 region limit.
Cylinder                           (float64, float64) Shape                        3D Cylinder with diameter and height in meter
DefRegion                          (int, Shape)                                    Define a material region with given index (0-255) and shape
DefRegionCell                      (int, int, int, int)                            Set a material region (first argument) in one cell by the index of the cell (last three arguments)
Div                                (Quantity, Quantity) Quantity                   Point-wise division of two quantities
Dot                                (Quantity, Quantity) Quantity                   Dot product of two vector quantities
Ellipse                            (float64, float64) Shape                        2D Ellipse with axes in meter
Ellipsoid                          (float64, float64, float64) Shape               3D Ellipsoid with axes in meter
erf                                (float64) float64
erfc                               (float64) float64
Exit                               ()                                              Exit from the program
exp                                (float64) float64
exp2                               (float64) float64
Expect                             (string, float64, float64, float64)             Used for automated tests: checks if a value is close enough to the expected value
ExpectB                            (string, bool, bool)                            Used for automated tests: checks if two booleans are equal
ExpectV                            (string, Vector, Vector, float64)               Used for automated tests: checks if a vector is close enough to the expected value
expm1                              (float64) float64
ext_AllRegionShapes                () func(int) Shape                              Returns a function that gives the shape of each region. Does not automatically update if the region is redefined or moved with Shift. Call as: allregions := ext_AllRegionShapes(); shape := allregions(i); on seperate lines. Note: double parentheses as ext_AllRegionShapes()(i) are not supported in mx3 scripts and must be split across two lines.
ext_centerBubble                   ()                                              centerBubble shifts m after each step to keep the bubble position close to the center of the window
ext_centerWall                     (int)                                           centerWall(c) shifts m after each step to keep m_c close to zero
ext_centerWallInLayer              (int, int)                                      centerWallInLayer(L, c) shifts m after each step to keep m_c in layer L close to zero
ext_centerWallInRegion             (int, int)                                      centerWallInRegion(R, c) shifts m after each step to keep m_c in region R close to zero
ext_EnableUnsafe                   ()                                              Deprecated. Only here to ensure maximal backwards compatibility with mumax3.9c.
ext_GeomEdge                       (string) Shape                                  Returns an edge (+x, -x, +y, -y, +z, -z) of the geometry as a Shape. The Shape may not update automatically after changes to the mesh or geometry; rerun the function to refresh.
ext_grainboundaries                (int, int, int, float64, int)                   (startregion, numgrains, offset, boundarythickness, zeroflag). Given existing regions, reassigns grain boundaries of boundarythickness to new region values, starting at offset. Zeroflag: 1 = region0 is normal, 0 = region0 acts as edge but no boundary itself, -1 = ignore region0 entirely. grainboundary_edgeX/Y/Z control whether simulatiion box edges are treated as grainboundaries.
ext_InitGeomFromOVF                (string)                                        Initialize geometry, cell count and cell size given a pattern from OVF
ext_InterDind                      (int, int, float64)                             Sets Dind coupling between two regions.
ext_InterExchange                  (int, int, float64)                             Sets exchange coupling between two regions.
ext_make3dgrains                   (float64, int, int, Shape, int)                 3D Voronoi tesselation over shape (grain size, starting region number, num regions, shape, seed)
ext_makegrains                     (float64, int, int)                             Voronoi tesselation (grain size, num regions, seed)
ext_rmSurfaceCharge                (int, float64, float64)                         Compensate magnetic charges on the left and right sides of an in-plane magnetized wire. Arguments: region, mx on left and right side, resp.
ext_ScaleDind                      (int, int, float64)                             Re-scales Dind coupling between two regions.
ext_ScaleExchange                  (int, int, float64)                             Re-scales exchange coupling between two regions.
floor                              (float64) float64
Flush                              ()                                              Flush all pending output to disk.
Fprintln                           (string, ...any)                                Print to file
FunctionFromDatafile               (string, int, int, string) func(float64) float64  Creates an interpolation function using data from two columns in a csv file. Arguments: filename, xColumnIdx, yColumnIdx, method ("linear", "nearest" or "step").
gamma                              (float64) float64
GetDemagExactEvals                 () int                                          Report exact demagnetizing-field convolutions performed while extrapolation was active
GetDemagExtrapolatedEvals          () int                                          Report demagnetizing-field convolutions replaced by polynomial extrapolation
GetDemagExtrapolationStatus        () string                                       Report the current demagnetizing-field extrapolation status or safety-disable reason
GetDemagRejectedAttempts           () int                                          Report rejected solver attempts handled while demagnetizing-field extrapolation was active
GrainRoughness                     (float64, float64, float64, int) Shape          Grainy surface with different heights per grain with a typical grain size (first argument), minimal height (second argument), and maximal height (third argument). The last argument is a seed for the random number generator.
heaviside                          (float64) float64                               Returns 1 if x>0, 0 if x<0, and 0.5 if x==0
Helical                            (Vector) Config                                 Helical state for given wave vector
HopfionCompactSupport              (float64, float64) Config                       Hopfion texture from skyrmion, with compact support (smooth and magnetization exactly along z-axis outside of finite region)
hypot                              (float64, float64) float64
ilogb                              (float64) int
ImageShape                         (string) Shape                                  Use black/white image as shape
Index2Coord                        (int, int, int) Vector                          Convert cell index to x,y,z coordinate in meter
IsDemagExtrapolationActive         () bool                                         Report whether demagnetizing-field extrapolation is active for the current solver step
isInf                              (float64, int) bool
isNaN                              (float64) bool
j0                                 (float64) float64
j1                                 (float64) float64
jn                                 (int, float64) float64
Layer                              (int) Shape                                     Single layer (along z), by integer index starting from 0. Note: based on the current cell size, so may no longer be valid if cell size is changed.
Layers                             (int, int) Shape                                Part of space between cell layer1 (inclusive) and layer2 (exclusive), in integer indices. Note: based on the current cell size, so may no longer be valid if cell size is changed.
ldexp                              (float64, int) float64
Line                               (float64, float64, float64, float64, float64, float64, float64, string) Shape  3D line segment between (x1, y1, z1) and (x2, y2, z2), with given diameter, in meter. Last element specifies the line cap, which can be 'infinite', 'round' or 'flat'. Using zero diameter creates a minimally connected geometry, unless it is later scaled/rotated.
Line2D                             (float64, float64, float64, float64, float64, string) Shape  2D equivalent of Line(), resulting in a uniform fill along the z-axis
LoadFile                           (string) Slice                                  Load a data file (ovf or dump)
log                                (float64) float64
log10                              (float64) float64
log1p                              (float64) float64
log2                               (float64) float64
logb                               (float64) float64
Madd                               (Quantity, Quantity, float64, float64) mAddition  Weighted addition: Madd(Q1,Q2,c1,c2) = c1*Q1 + c2*Q2
Masked                             (Quantity, Shape) Quantity                      Mask quantity with shape
max                                (float64, float64) float64
min                                (float64, float64) float64
Minimize                           () bool                                         Use steepest conjugate gradient method to minimize the total energy. Returns true if convergence is reached, or false if the wall-clock time limit is exceeded. The wall-clock time limit is disabled by default.
mod                                (float64, float64) float64
Mul                                (Quantity, Quantity) Quantity                   Point-wise product of two quantities
MulMV                              (Quantity, Quantity, Quantity, Quantity) Quantity  Matrix-Vector product: MulMV(AX, AY, AZ, m) = (AX·m, AY·m, AZ·m). The arguments Ax, Ay, Az and m are quantities with 3 componets.
NeelSkyrmion                       (int, int) Config                               Néél skyrmion magnetization with given charge and core polarization
NewScalarMask                      (int, int, int) Slice                           Makes a 3D array of scalars
NewSlice                           (int, int, int, int) Slice                      Makes a 4D array with a specified number of components (first argument) and a specified size nx,ny,nz (remaining arguments)
NewVectorMask                      (int, int, int) Slice                           Makes a 3D array of vectors
norm                               (float64) float64                               Standard normal distribution
Normalized                         (Quantity) Quantity                             Normalize quantity
now                                () time.Time                                    Returns the current time
pow                                (float64, float64) float64
pow10                              (int) float64
Print                              (...any)                                        Print to standard output
rand                               () float64                                      Random number between 0 and 1
randExp                            () float64                                      Exponentially distributed random number between 0 and +inf, mean=1
randInt                            (int) int                                       Random non-negative integer
randNorm                           () float64                                      Standard normal random number
RandomMag                          () Config                                       Random magnetization
RandomMagSeed                      (int) Config                                    Random magnetization with given seed
randSeed                           (int)                                           Sets the random number seed for rand(), randExp(), randNorm() and randInt().
Rect                               (float64, float64) Shape                        2D rectangle with size in meter
RedefRegion                        (int, int)                                      Reassign all cells with a given region (first argument) to a new region (second argument)
Relax                              () bool                                         Try to minimize the total energy. Returns true if convergence is reached, or false if the wall-clock time limit is exceeded. The wall-clock time limit is disabled by default.
remainder                          (float64, float64) float64
RemoveCustomEnergies               ()                                              Removes all custom energies
RemoveCustomFields                 ()                                              Removes all custom fields again
ResetDemagExtrapolation            ()                                              Discard all demagnetizing-field extrapolation history and counters
Run                                (float64)                                       Run the simulation for a time in seconds
RunningAverage                     (Quantity) Quantity                             Records the time-average of a quantity from the moment this function is called. Note: this may impact performance since the Quantity will be evaluated after every step.
RunWhile                           (func() bool)                                   Run while condition function is true
Save                               (Quantity)                                      Save space-dependent quantity once, with auto filename
SaveAs                             (Quantity, string)                              Save space-dependent quantity with custom filename
SetCellSize                        (float64, float64, float64)                     Sets the X,Y,Z cell size in meters
SetGeom                            (Shape)                                         Sets the geometry to a given shape
SetGridSize                        (int, int, int)                                 Sets the number of cells for X,Y,Z
SetMesh                            (int, int, int, float64, float64, float64, int, int, int)  Sets GridSize, CellSize and PBC at the same time
SetPBC                             (int, int, int)                                 Sets the number of repetitions in X,Y,Z to create periodic boundary conditions. The number of repetitions determines the cutoff range for the demagnetization.
SetSolver                          (int)                                           Set solver type. 1: Euler 2: Heun 3: Bogacki-Shampine 4: Runge-Kutta (RK4) 5: Dormand-Prince 6: Fehlberg -1: Backward Euler
Shift                              (int)                                           Shifts the simulation by +1/-1 cells along X
Shifted                            (Quantity, int, int, int) Quantity              Shifted quantity
Sign                               (float64) float64                               Signum function
sin                                (float64) float64
sinc                               (float64) float64                               Sinc returns sin(x)/x. If x=0, then Sinc(x) returns 1.
since                              (time.Time) time.Duration                       Returns the time elapsed since argument
sinh                               (float64) float64
Snapshot                           (Quantity)                                      Save image of quantity
SnapshotAs                         (Quantity, string)                              Save image of quantity with custom filename
sprint                             (...any) string                                 Print all arguments to string with automatic formatting
sprintf                            (string, ...any) string                         Print to string with C-style formatting.
sqrt                               (float64) float64
Square                             (float64) Shape                                 2D square with size in meter
Steps                              (int)                                           Run the simulation for a number of time steps
Sum                                (Quantity) float64                              Sum of Quantity over all cells in the grid. For a vector Quantity, all components are added together.
SumVector                          (Quantity) Vector                               Sum of vector Quantity over all cells in the grid.
Superball                          (float64, float64) Shape                        3D Superball with diameter in meter and shape parameter p. Interpolates between a cube (p=+∞), sphere (p=1), octahedron (p=0.5) and empty space (p≤0).
TableAdd                           (Quantity)                                      Add quantity as a column to the data table.
TableAddVar                        (ScalarFunction, string, string)                Add user-defined variable + name + unit to data table.
TableAutoSave                      (float64)                                       Auto-save the data table every period (s). Zero disables save.
TablePrint                         (...any)                                        Print anyting in the data table
TableSave                          ()                                              Save the data table right now (appends one line).
tan                                (float64) float64
tanh                               (float64) float64
ThermSeed                          (int)                                           Set a random seed for thermal noise
Triangle                           (float64, float64, float64, float64, float64, float64) Shape  2D triangle with vertices (x0, y0), (x1, y1) and (x2, y2)
trunc                              (float64) float64
TwoDomain                          (float64, float64, float64, float64, float64, float64, float64, float64, float64) Config  Twodomain magnetization with with given magnetization in left domain, wall, and right domain
Uniform                            (float64, float64, float64) Config              Uniform magnetization in given direction
Universe                           () Shape                                        Entire space
Vector                             (float64, float64, float64) Vector              Constructs a vector with given components
Vortex                             (int, int) Config                               Vortex magnetization with given circulation and core polarization
VortexWall                         (float64, float64, int, int) Config             Vortex wall magnetization with given mx in left and right domain and core circulation and polarization
VoxelShape                         (Slice, float64, float64, float64) Shape        Use slice (ScalarMask containing 0s and 1s) of rectangular cells (with size defined by last 3 arguments) as a 3D object
XRange                             (float64, float64) Shape                        Part of space between x1 (inclusive) and x2 (exclusive), in meter
y0                                 (float64) float64
y1                                 (float64) float64
yn                                 (int, float64) float64
YRange                             (float64, float64) Shape                        Part of space between y1 (inclusive) and y2 (exclusive), in meter
ZRange                             (float64, float64) Shape                        Part of space between z1 (inclusive) and z2 (exclusive), in meter
```

## Variables

Assign with `Name = value`; read where a quantity is accepted.

```
Aex                                RegionwiseScalar                                Exchange stiffness (J/m)
alpha                              RegionwiseScalar                                Landau-Lifshitz damping constant
anisC1                             RegionwiseVector                                Cubic anisotropy direction #1
anisC2                             RegionwiseVector                                Cubic anisotropy direction #2
anisU                              RegionwiseVector                                Uniaxial anisotropy direction
B1                                 RegionwiseScalar                                First magneto-elastic coupling constant (J/m3)
B2                                 RegionwiseScalar                                Second magneto-elastic coupling constant (J/m3)
B_anis                             VectorField                                     Anisotropy field (T)
B_custom                           VectorField                                     User-defined field (T)
B_demag                            VectorField                                     Magnetostatic field (T)
B_eff                              VectorField                                     Effective field (T)
B_exch                             VectorField                                     Exchange field (T)
B_ext                              Excitation                                      Externally applied field (T)
B_mel                              VectorField                                     Magneto-elastic filed (T)
B_therm                            thermField                                      Thermal field (T)
Dbulk                              RegionwiseScalar                                Bulk Dzyaloshinskii-Moriya strength (J/m2)
DemagAccuracy                      float64                                         Controls accuracy of demag kernel
DemagExtrapolation                 bool                                            Experimental approximate demagnetizing-field extrapolation for solver 4 (RK4), 5 (Dormand-Prince), or 6 (Fehlberg) only (default=false). This changes numerical results; validate trajectory and energy against DemagExtrapolation=false for each workload
Dind                               RegionwiseScalar                                Interfacial Dzyaloshinskii-Moriya strength (J/m2)
DindCoupling                       ScalarField                                     Average DMI coupling with neighbors (arb.)
DisableSlonczewskiTorque           bool                                            Disables Slonczewski torque (default=false)
DisableZhangLiTorque               bool                                            Disables Zhang-Li torque (default=false)
DoPrecess                          bool                                            Enables LL precession (default=true)
dt                                 ScalarValue                                     Time Step (s)
DUMP                               OutputFormat                                    OutputFormat = DUMP sets text DUMP output
E_anis                             ScalarValue                                     total anisotropy energy (J)
E_custom                           ScalarValue                                     total energy of user-defined field (J)
E_demag                            ScalarValue                                     Magnetostatic energy (J)
E_exch                             ScalarValue                                     Total exchange energy (including the DMI energy) (J)
E_mel                              ScalarValue                                     Magneto-elastic energy (J)
E_therm                            ScalarValue                                     Thermal energy (J)
E_total                            ScalarValue                                     total energy (J)
E_Zeeman                           ScalarValue                                     Zeeman energy (J)
Edens_anis                         ScalarField                                     Anisotropy energy density (J/m3)
Edens_custom                       ScalarField                                     Energy density of user-defined field. (J/m3)
Edens_demag                        ScalarField                                     Magnetostatic energy density (J/m3)
Edens_exch                         ScalarField                                     Total exchange energy density (including the DMI energy density) (J/m3)
Edens_mel                          ScalarField                                     Magneto-elastic energy density (J/m3)
Edens_therm                        ScalarField                                     Thermal energy density (J/m3)
Edens_total                        ScalarField                                     Total energy density (J/m3)
Edens_Zeeman                       ScalarField                                     Zeeman energy density (J/m3)
EdgeCarryShift                     bool                                            Whether to use the current magnetization at the border for the cells inserted by Shift (default=false)
EdgeSmooth                         int                                             Geometry edge smoothing with edgeSmooth^3 samples per cell, 0=staircase, ~8=very smooth
EnableDemag                        bool                                            Enables/disables demag (default=true)
EpsilonPrime                       RegionwiseScalar                                Slonczewski secondairy STT term ε'
ExchCoupling                       ScalarField                                     Average exchange coupling with neighbors (arb.)
ext_BackGroundTilt                 float64                                         Size of in-plane component of background magnetization. All values below this one are rounded down to perfectly out-of-plane to improve position calculation (default = 0.25)
ext_bubbledist                     ScalarValue                                     Bubble traveled distance (m)
ext_BubbleMz                       float64                                         Center magnetization 1.0 or -1.0 (default = 1.0)
ext_bubblepos                      VectorValue                                     Bubble core position (m)
ext_bubblespeed                    ScalarValue                                     Bubble velocity (m/s)
ext_corepos                        VectorValue                                     Vortex core position (x,y) + polarization (z) (m)
ext_dwpos                          ScalarValue                                     Position of the simulation window while following a domain wall (m)
ext_dwspeed                        ScalarValue                                     Speed of the simulation window while following a domain wall (m/s)
ext_dwtilt                         ScalarValue                                     PMA domain wall tilt (rad)
ext_dwxpos                         ScalarValue                                     Position of the simulation window while following a domain wall (m)
ext_emergentmagneticfield_fivepointstencil VectorField                                     Emergent magnetic field calculated using five-point stencil (1/m2)
ext_emergentmagneticfield_solidangle VectorField                                     Emergent magnetic field computed using Berg-Lüscher lattice method (1/m2)
ext_emergentmagneticfield_twopointstencil VectorField                                     Emergent magnetic field calculated using two-point stencil (1/m2)
ext_enableCenterBubbleX            bool                                            Enables centering along the X-axis during ext_centerBubble (default=true)
ext_enableCenterBubbleY            bool                                            Enables centering along the Y-axis during ext_centerBubble (default=true)
ext_grainboundary_edgeX            bool                                            Treat X edges of simulation box as boundaries. Ignored if PBC in X direction enabled (default= true)
ext_grainboundary_edgeY            bool                                            Treat Y edges of simulation box as boundaries. Ignored if PBC in Y direction enabled (default= true)
ext_grainboundary_edgeZ            bool                                            Treat Z edges of simulation box as boundaries. Ignored if PBC in Z direction enabled (default= false)
ext_grainCutShape                  bool                                            Whether to add the complete (3D) voronoi grain, only if its centre lies within the shape (default=false)
ext_hopfindex_fivepointstencil     ScalarValue                                     Hopf index calculated using five-point stencil
ext_hopfindex_solidangle           ScalarValue                                     Hopf index calculated using Berg-Lüscher lattice method
ext_hopfindex_solidanglefourier    ScalarValue                                     Hopf index calculated using Berg-Lüscher lattice method to calculate emergent field, with emergent field Fourier transformed
ext_hopfindex_twopointstencil      ScalarValue                                     Hopf index calculated using two-point stencil
ext_hopfindexdensity_fivepointstencil ScalarField                                     Hopf index density calculated using five-point stencil (1/m3)
ext_hopfindexdensity_solidangle    ScalarField                                     Hopf index density computed using Berg-Lüscher lattice method (1/m3)
ext_hopfindexdensity_twopointstencil ScalarField                                     Hopf index density calculated using two-point stencil (1/m3)
ext_phi                            ScalarField                                     Azimuthal angle (rad)
ext_theta                          ScalarField                                     Polar angle (rad)
ext_topologicalcharge              ScalarValue                                     2D topological charge
ext_topologicalchargedensity       ScalarField                                     2D topological charge density m·(∂m/∂x ✕ ∂m/∂y) (1/m2)
ext_topologicalchargedensitylattice ScalarField                                     2D topological charge density according to Berg and Lüscher (1/m2)
ext_topologicalchargelattice       ScalarValue                                     2D topological charge according to Berg and Lüscher
exx                                ScalarExcitation                                exx component of the strain tensor
exy                                ScalarExcitation                                exy component of the strain tensor
exz                                ScalarExcitation                                exz component of the strain tensor
eyy                                ScalarExcitation                                eyy component of the strain tensor
eyz                                ScalarExcitation                                eyz component of the strain tensor
ezz                                ScalarExcitation                                ezz component of the strain tensor
F_mel                              VectorField                                     Magneto-elastic force density (N/m3)
false                              bool
FilenameFormat                     string                                          printf formatting string for output filenames.
FixDt                              float64                                         Set a fixed time step, 0 disables fixed step (which is the default)
FixedLayer                         Excitation                                      Slonczewski fixed layer polarization
FIXEDLAYER_BOTTOM                  FixedLayerPosition                              FixedLayerPosition = FIXEDLAYER_BOTTOM instructs mumax3 that fixed layer is underneath of the free layer
FIXEDLAYER_TOP                     FixedLayerPosition                              FixedLayerPosition = FIXEDLAYER_TOP instructs mumax3 that fixed layer is on top of the free layer
FixedLayerPosition                 FixedLayerPosition                              Position of the fixed layer: FIXEDLAYER_TOP, FIXEDLAYER_BOTTOM (default=FIXEDLAYER_TOP)
FreeLayerThickness                 RegionwiseScalar                                Slonczewski free layer thickness (if set to zero (default), then the thickness will be deduced from the mesh size) (m)
frozenspins                        RegionwiseScalar                                Defines spins that should be fixed
GammaLL                            float64                                         Gyromagnetic ratio in rad/Ts
geom                               geom                                            Cell fill fraction (0..1)
Headroom                           float64                                         Solver headroom (default = 0.8)
inf                                float64
J                                  Excitation                                      Electrical current density (A/m2)
Kc1                                RegionwiseScalar                                1st order cubic anisotropy constant (J/m3)
Kc2                                RegionwiseScalar                                2nd order cubic anisotropy constant (J/m3)
Kc3                                RegionwiseScalar                                3rd order cubic anisotropy constant (J/m3)
Ku1                                RegionwiseScalar                                1st order uniaxial anisotropy constant (J/m3)
Ku2                                RegionwiseScalar                                2nd order uniaxial anisotropy constant (J/m3)
Lambda                             RegionwiseScalar                                Slonczewski Λ parameter
LastErr                            ScalarValue                                     Error of last step
LLtorque                           VectorField                                     Landau-Lifshitz torque/γ0 (T)
m                                  magnetization                                   Reduced magnetization (unit length)
m_full                             VectorField                                     Unnormalized magnetization (A/m)
MaxAngle                           ScalarValue                                     maximum angle between neighboring spins (rad)
MaxDt                              float64                                         Maximum time step the solver can take (s)
MaxErr                             float64                                         Maximum error per step the solver can tolerate (default = 1e-5)
maxTorque                          ScalarValue                                     Maximum torque/γ0, over all cells (T)
MFM                                ScalarField                                     MFM image (arb.)
MFMDipole                          float64                                         Height of vertically magnetized part of MFM tip
MFMLift                            float64                                         MFM lift height
MinDt                              float64                                         Minimum time step the solver can take (s)
MinimizeOnGPU                      bool                                            Keep the Minimize step size in device memory so an iteration does not drain the GPU pipeline (default=false). Each descent is bit-identical; the convergence check is one iteration late, so a minimization may take one extra step.
MinimizerSamples                   int                                             Number of max dM to collect for Minimize convergence check.
MinimizerStop                      float64                                         Stopping max dM for Minimize
MinimizeWallClockTime              float64                                         Wall-clock time limit (seconds) for Minimize that will interrupt the minimization if exceeded. Set to -1 (default) to disable. An interrupted minimization does not guarantee a correct solution.
Msat                               RegionwiseScalar                                Saturation magnetization (A/m)
Mu0                                float64                                         Vacuum permeability (Tm/A)
NEval                              ScalarValue                                     Total number of torque evaluations
NoDemagSpins                       RegionwiseScalar                                Disable magnetostatic interaction per region (default=0, set to 1 to disable). E.g.: NoDemagSpins.SetRegion(5, 1) disables the magnetostatic interaction in region 5.
NREGION                            int                                             Maximum number of regions (256)
OpenBC                             bool                                            Use open boundary conditions (default=false)
OutputFormat                       OutputFormat                                    Format for data files: OVF1_TEXT, OVF1_BINARY, OVF2_TEXT or OVF2_BINARY
OVF1_BINARY                        OutputFormat                                    OutputFormat = OVF1_BINARY sets binary OVF1 output
OVF1_TEXT                          OutputFormat                                    OutputFormat = OVF1_TEXT sets text OVF1 output
OVF2_BINARY                        OutputFormat                                    OutputFormat = OVF2_BINARY sets binary OVF2 output
OVF2_TEXT                          OutputFormat                                    OutputFormat = OVF2_TEXT sets text OVF2 output
PeakErr                            ScalarValue                                     Overall maxium error per step
pi                                 float64
Pol                                RegionwiseScalar                                Electrical current polarization
regions                            Regions                                         Outputs the region index for each cell
RelaxTorqueThreshold               float64                                         MaxTorque threshold for relax(). If set to -1 (default), relax() will stop when the average torque is steady or increasing.
RelaxWallClockTime                 float64                                         Wall-clock time limit (seconds) for Relax that will interrupt the relaxation if exceeded. Set to -1 (default) to disable.
ShiftGeom                          bool                                            Whether Shift() acts on geometry
ShiftM                             bool                                            Whether Shift() acts on magnetization
ShiftMagD                          Vector                                          Upon shift, insert this magnetization from the bottom
ShiftMagL                          Vector                                          Upon shift, insert this magnetization from the left
ShiftMagR                          Vector                                          Upon shift, insert this magnetization from the right
ShiftMagU                          Vector                                          Upon shift, insert this magnetization from the top
ShiftRegions                       bool                                            Whether Shift() acts on regions
SnapshotFormat                     string                                          Image format for snapshots: jpg, png or gif.
SpeculativeStep                    bool                                            Overlap host encoding with GPU execution by judging an adaptive step one step late (default=false). Error rejection still enforces MaxErr, but the sequence of time steps differs from the exact controller, so validate against SpeculativeStep=false for each workload
spinAngle                          ScalarField                                     Angle between neighboring spins (rad)
step                               int                                             Total number of time steps taken
STTorque                           VectorField                                     Spin-transfer torque/γ0 (T)
t                                  float64                                         Total simulated time (s)
Temp                               RegionwiseScalar                                Temperature (K)
torque                             VectorField                                     Total torque/γ0 (T)
TotalShift                         float64                                         Amount by which the simulation has been shifted along the x-axis (m).
true                               bool
xi                                 RegionwiseScalar                                Non-adiabaticity of spin-transfer-torque
```

## Methods

Call on a value of the receiver type: `Msat.SetRegion(1, 800e3)`, `Circle(1e-7).Add(...)`.

```
Config.Add                         (float64, Config) Config
Config.RotZ                        (float64) Config
Config.Scale                       (float64, float64, float64) Config
Config.Transl                      (float64, float64, float64) Config
cropped.Average                    () []float64
cropped.Name                       () string
cropped.Unit                       () string
error.Error                        () string
Excitation.Add                     (Slice, ScalarFunction)
Excitation.Average                 () Vector
Excitation.Comp                    (int) ScalarField
Excitation.IsUniform               () bool
Excitation.Name                    () string
Excitation.Region                  (int) vOneReg
Excitation.RemoveExtraTerms        ()
Excitation.Set                     (Vector)
Excitation.SetRegion               (int, VectorFunction)
Excitation.Unit                    () string
geom.Average                       () float64
geom.GetCell                       (int, int, int) float64
geom.Name                          () string
geom.Unit                          () string
magnetization.Average              () Vector
magnetization.Comp                 (int) ScalarField
magnetization.GetCell              (int, int, int) Vector
magnetization.LoadFile             (string)
magnetization.Name                 () string
magnetization.Region               (int) vOneReg
magnetization.Set                  (Config)
magnetization.SetArray             (Slice)
magnetization.SetCell              (int, int, int, Vector)
magnetization.SetInShape           (Shape, Config)
magnetization.SetRegion            (int, Config)
magnetization.Unit                 () string
Regions.Average                    () float64
Regions.GetCell                    (int, int, int) int
Regions.LoadFile                   (string)
Regions.Name                       () string
Regions.SetCell                    (int, int, int, int)
Regions.Unit                       () string
RegionwiseScalar.Average           () float64
RegionwiseScalar.GetRegion         (int) float64
RegionwiseScalar.IsUniform         () bool
RegionwiseScalar.Name              () string
RegionwiseScalar.Region            (int) sOneReg
RegionwiseScalar.Set               (float64)
RegionwiseScalar.SetRegion         (int, ScalarFunction)
RegionwiseScalar.Unit              () string
RegionwiseVector.Average           () Vector
RegionwiseVector.Comp              (int) ScalarField
RegionwiseVector.GetRegion         (int) [3]float64
RegionwiseVector.IsUniform         () bool
RegionwiseVector.Name              () string
RegionwiseVector.Region            (int) vOneReg
RegionwiseVector.SetRegion         (int, VectorFunction)
RegionwiseVector.Unit              () string
ScalarExcitation.Add               (Slice, ScalarFunction)
ScalarExcitation.Average           () float64
ScalarExcitation.Comp              (int) ScalarField
ScalarExcitation.IsUniform         () bool
ScalarExcitation.Name              () string
ScalarExcitation.Region            (int) vOneReg
ScalarExcitation.RemoveExtraTerms  ()
ScalarExcitation.Set               (float64)
ScalarExcitation.SetRegion         (int, ScalarFunction)
ScalarExcitation.Unit              () string
ScalarField.Average                () float64
ScalarField.Name                   () string
ScalarField.Region                 (int) ScalarField
ScalarField.Unit                   () string
ScalarValue.Average                () float64
ScalarValue.Get                    () float64
ScalarValue.Name                   () string
ScalarValue.Unit                   () string
Shape.Add                          (Shape) Shape
Shape.Intersect                    (Shape) Shape
Shape.Inverse                      () Shape
Shape.Repeat                       (float64, float64, float64) Shape
Shape.RotX                         (float64) Shape
Shape.RotY                         (float64) Shape
Shape.RotZ                         (float64) Shape
Shape.Scale                        (float64, float64, float64) Shape
Shape.Sub                          (Shape) Shape
Shape.Transl                       (float64, float64, float64) Shape
Shape.Xor                          (Shape) Shape
Slice.Comp                         (int) Slice
Slice.Contiguous                   () bool
Slice.CPUAccess                    () bool
Slice.DevPtr                       (int) unsafe.Pointer
Slice.Disable                      ()
Slice.Free                         ()
Slice.Get                          (int, int, int, int) float64
Slice.GPUAccess                    () bool
Slice.Host                         () [][]float32
Slice.Index                        (int, int, int) int
Slice.IsNil                        () bool
Slice.Len                          () int
Slice.MemType                      () int
Slice.OwnsStorage                  () bool
Slice.Scalars                      () [][][]float32
Slice.Set                          (int, int, int, int, float64)
Slice.SetScalar                    (int, int, int, float64)
Slice.SetVector                    (int, int, int, Vector)
Slice.Size                         () [3]int
Slice.Tensors                      () [][][][]float32
Slice.Vectors                      () [3][][][]float32
sOneReg.Average                    () float64
sOneReg.Name                       () string
sOneReg.Unit                       () string
thermField.Name                    () string
thermField.Unit                    () string
time.Duration.Abs                  () time.Duration
time.Duration.Hours                () float64
time.Duration.Microseconds         () int64
time.Duration.Milliseconds         () int64
time.Duration.Minutes              () float64
time.Duration.Nanoseconds          () int64
time.Duration.Round                (time.Duration) time.Duration
time.Duration.Seconds              () float64
time.Duration.Truncate             (time.Duration) time.Duration
time.Time.Add                      (time.Duration) time.Time
time.Time.AddDate                  (int, int, int) time.Time
time.Time.After                    (time.Time) bool
time.Time.AppendBinary             ([]uint8) []uint8, error
time.Time.AppendFormat             ([]uint8, string) []uint8
time.Time.AppendText               ([]uint8) []uint8, error
time.Time.Before                   (time.Time) bool
time.Time.Clock                    () int, int, int
time.Time.Compare                  (time.Time) int
time.Time.Date                     () int, time.Month, int
time.Time.Day                      () int
time.Time.Equal                    (time.Time) bool
time.Time.Format                   (string) string
time.Time.GobEncode                () []uint8, error
time.Time.GoString                 () string
time.Time.Hour                     () int
time.Time.In                       (time.Location) time.Time
time.Time.IsDST                    () bool
time.Time.ISOWeek                  () int, int
time.Time.IsZero                   () bool
time.Time.Local                    () time.Time
time.Time.Location                 () time.Location
time.Time.MarshalBinary            () []uint8, error
time.Time.MarshalJSON              () []uint8, error
time.Time.MarshalText              () []uint8, error
time.Time.Minute                   () int
time.Time.Month                    () time.Month
time.Time.Nanosecond               () int
time.Time.Round                    (time.Duration) time.Time
time.Time.Second                   () int
time.Time.Sub                      (time.Time) time.Duration
time.Time.Truncate                 (time.Duration) time.Time
time.Time.Unix                     () int64
time.Time.UnixMicro                () int64
time.Time.UnixMilli                () int64
time.Time.UnixNano                 () int64
time.Time.UTC                      () time.Time
time.Time.Weekday                  () time.Weekday
time.Time.Year                     () int
time.Time.YearDay                  () int
time.Time.Zone                     () string, int
time.Time.ZoneBounds               () time.Time, time.Time
Vector.Add                         (Vector) Vector
Vector.Cross                       (Vector) Vector
Vector.Div                         (float64) Vector
Vector.Dot                         (Vector) float64
Vector.Len                         () float64
Vector.MAdd                        (float64, Vector) Vector
Vector.Mul                         (float64) Vector
Vector.Sub                         (Vector) Vector
Vector.X                           () float64
Vector.Y                           () float64
Vector.Z                           () float64
VectorField.Average                () Vector
VectorField.Comp                   (int) ScalarField
VectorField.Name                   () string
VectorField.Region                 (int) VectorField
VectorField.Unit                   () string
VectorValue.Average                () Vector
VectorValue.Get                    () Vector
VectorValue.Name                   () string
VectorValue.Unit                   () string
vOneReg.Average                    () Vector
vOneReg.Name                       () string
vOneReg.Unit                       () string
```

