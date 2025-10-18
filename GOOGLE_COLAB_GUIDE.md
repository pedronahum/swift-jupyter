# Google Colab Installation Guide

This guide shows you how to install and use the Swift Jupyter kernel in Google Colab.

## Quick Start (One-Click Install)

### Step 1: Open Google Colab

1. Go to [Google Colab](https://colab.research.google.com)
2. Create a new notebook (File → New notebook)

### Step 2: Run Installation Script

Copy and paste this into a code cell and run it:

```bash
!curl -s https://raw.githubusercontent.com/pedronahum/swift-jupyter/main/install_swift_colab.sh | bash
```

**Installation time**: ~3-5 minutes

The script will:
- ✅ Download Swift 6.3 Development Snapshot (October 10, 2024)
- ✅ Install all system dependencies
- ✅ Install Jupyter kernel dependencies
- ✅ Register the Swift kernel
- ✅ Create a test notebook at `/content/swift_test.ipynb`

### Step 3: Restart Runtime

After installation completes:

1. Click **Runtime** → **Restart runtime**
2. Wait for the runtime to restart (~10 seconds)

### Step 4: Verify Installation

Run this in a Python cell to verify the kernel is registered:

```python
!jupyter kernelspec list
```

You should see output like:
```
Available kernels:
  python3    /usr/local/share/jupyter/kernels/python3
  swift      /usr/local/share/jupyter/kernels/swift
```

### Step 5: Use Swift!

Now you have two options:

#### Option A: Change Runtime Type

1. Click **Runtime** → **Change runtime type**
2. Under "Runtime type", select **Swift**
3. Click **Save**
4. Your notebook now runs Swift code!

#### Option B: Open the Test Notebook

1. In the file browser (left sidebar), navigate to `/content/`
2. Open `swift_test.ipynb`
3. This notebook demonstrates Swift features

## What's Supported

### ✅ Core Swift Features

All standard Swift 6.3 features work:

```swift
// Variables and constants
let name = "Swift in Colab"
var count = 42

// Functions
func fibonacci(_ n: Int) -> Int {
    guard n > 1 else { return n }
    return fibonacci(n - 1) + fibonacci(n - 2)
}

print(fibonacci(10))  // 55

// Structs and classes
struct Point {
    var x: Double
    var y: Double

    func distance(to other: Point) -> Double {
        let dx = x - other.x
        let dy = y - other.y
        return (dx*dx + dy*dy).squareRoot()
    }
}

let p1 = Point(x: 0, y: 0)
let p2 = Point(x: 3, y: 4)
print(p1.distance(to: p2))  // 5.0
```

### ✅ Arrays, Dictionaries, Sets

```swift
// Arrays
let numbers = [1, 2, 3, 4, 5]
let doubled = numbers.map { $0 * 2 }
print(doubled)  // [2, 4, 6, 8, 10]

// Dictionaries
var scores = ["Alice": 95, "Bob": 87, "Charlie": 92]
scores["David"] = 88
print(scores)

// Sets
let unique = Set([1, 2, 2, 3, 3, 3, 4])
print(unique)  // {1, 2, 3, 4}
```

### ✅ Protocols and Generics

```swift
protocol Describable {
    func describe() -> String
}

struct Person: Describable {
    let name: String
    let age: Int

    func describe() -> String {
        return "\(name), age \(age)"
    }
}

func printDescription<T: Describable>(_ item: T) {
    print(item.describe())
}

let person = Person(name: "Alice", age: 30)
printDescription(person)
```

### ✅ Error Handling

```swift
enum MathError: Error {
    case divisionByZero
}

func divide(_ a: Double, by b: Double) throws -> Double {
    guard b != 0 else { throw MathError.divisionByZero }
    return a / b
}

do {
    let result = try divide(10, by: 2)
    print("Result: \(result)")
} catch {
    print("Error: \(error)")
}
```

### ✅ SwiftPM Packages

You can install Swift packages using `%install`:

```swift
// IMPORTANT: %install MUST be in the FIRST CELL of your notebook
%install '.package(url: "https://github.com/apple/swift-algorithms", from: "1.0.0")' Algorithms
```

Then in subsequent cells:

```swift
import Algorithms

let numbers = [1, 2, 3, 4, 5]
for combo in numbers.combinations(ofCount: 2) {
    print(combo)
}
```

### ✅ PythonKit for Python Integration (matplotlib, numpy, pandas)

**Cell 1** (MUST be first cell):
```swift
%install '.package(url: "https://github.com/pvieito/PythonKit", branch: "master")' PythonKit
```

**Cell 2** - Setup:
```swift
%include "EnableIPythonDisplay.swift"
import PythonKit

// Import Python libraries
let np = Python.import("numpy")
let plt = Python.import("matplotlib.pyplot")

// Enable inline plotting
IPythonDisplay.shell.enable_matplotlib("inline")
```

**Cell 3** - Create plots:
```swift
// Create data
let x = np.linspace(0, 2 * np.pi, 100)
let y = np.sin(x)

// Plot
plt.figure(figsize: [10, 6])
plt.plot(x, y, label: "sin(x)", color: "blue", linewidth: 2)
plt.xlabel("x")
plt.ylabel("y")
plt.title("Sine Wave from Swift!")
plt.legend()
plt.grid(true)
plt.show()
```

### ✅ Data Science with pandas

```swift
import PythonKit

let pd = Python.import("pandas")
let np = Python.import("numpy")

// Create a DataFrame
let data = [
    "Name": ["Alice", "Bob", "Charlie", "David"],
    "Age": [25, 30, 35, 28],
    "Score": [95, 87, 92, 88]
]

let df = pd.DataFrame(data)
print(df)

// Basic statistics
print("\nMean age:", df["Age"].mean())
print("Max score:", df["Score"].max())

// Filtering
let young = df[df["Age"] < 30]
print("\nPeople under 30:")
print(young)
```

### ✅ NumPy Arrays

```swift
import PythonKit

let np = Python.import("numpy")

// Create arrays
let a = np.array([1, 2, 3, 4, 5])
let b = np.arange(10, 15)

// Operations
print("a + b =", a + b)
print("a * 2 =", a * 2)
print("Mean:", a.mean())
print("Std:", a.std())

// Multi-dimensional arrays
let matrix = np.array([[1, 2, 3], [4, 5, 6]])
print("\nMatrix shape:", matrix.shape)
print("Matrix transpose:\n", matrix.T)
```

## Complete Example Notebook

Here's a complete example you can copy-paste into Google Colab after installation:

### Cell 1: Install PythonKit
```swift
%install '.package(url: "https://github.com/pvieito/PythonKit", branch: "master")' PythonKit
```

### Cell 2: Setup
```swift
%include "EnableIPythonDisplay.swift"
import PythonKit

let np = Python.import("numpy")
let plt = Python.import("matplotlib.pyplot")
let pd = Python.import("pandas")

IPythonDisplay.shell.enable_matplotlib("inline")
print("✅ Python libraries loaded successfully!")
```

### Cell 3: Generate Data
```swift
// Generate sample data
let days = np.arange(1, 31)
let temperatures = 20 + 10 * np.sin(days * np.pi / 15) + np.random.randn(30) * 2
let humidity = 60 + 15 * np.cos(days * np.pi / 12) + np.random.randn(30) * 3

print("Generated 30 days of weather data")
```

### Cell 4: Create DataFrame
```swift
// Create pandas DataFrame
let weatherData = pd.DataFrame([
    "Day": days,
    "Temperature": temperatures,
    "Humidity": humidity
])

print(weatherData.head(10))
print("\nStatistics:")
print(weatherData.describe())
```

### Cell 5: Plot Data
```swift
// Create visualizations
let fig = plt.figure(figsize: [14, 5])

// Temperature plot
plt.subplot(1, 2, 1)
plt.plot(days, temperatures, marker: "o", linestyle: "-", color: "red", alpha: 0.7)
plt.xlabel("Day")
plt.ylabel("Temperature (°C)")
plt.title("Daily Temperature")
plt.grid(true, alpha: 0.3)

// Humidity plot
plt.subplot(1, 2, 2)
plt.plot(days, humidity, marker: "s", linestyle: "-", color: "blue", alpha: 0.7)
plt.xlabel("Day")
plt.ylabel("Humidity (%)")
plt.title("Daily Humidity")
plt.grid(true, alpha: 0.3)

plt.tight_layout()
plt.show()
```

### Cell 6: Statistical Analysis
```swift
// Calculate correlations
let correlation = np.corrcoef([temperatures, humidity])[0][1]
print("Temperature-Humidity Correlation:", correlation)

// Find extremes
let maxTempDay = Int(np.argmax(temperatures))! + 1
let minTempDay = Int(np.argmin(temperatures))! + 1

print("\nHottest day: Day \(maxTempDay)")
print("Coldest day: Day \(minTempDay)")

// Average values
print("\nAverage temperature:", Double(temperatures.mean())!, "°C")
print("Average humidity:", Double(humidity.mean())!, "%")
```

## What's Currently NOT Supported

### ❌ Swift for TensorFlow Features

The following require the archived Swift for TensorFlow toolchains:

- `@differentiable` attribute
- Built-in `TensorFlow` module
- Built-in `_Differentiation` module
- Built-in `Python` module (use PythonKit instead)

### ❌ Native iOS/macOS UI Frameworks

- SwiftUI (requires iOS/macOS runtime)
- UIKit/AppKit (requires iOS/macOS runtime)
- Apple's Charts framework (use matplotlib instead)

### ⚠️ Known Limitations

1. **%install must be in first cell**: SwiftPM packages must be installed before any other Swift code runs

2. **Long compilation times**: First time installing packages takes ~5-10 minutes (PythonKit, etc.)

3. **No package persistence**: Packages are not saved between Colab sessions. You must run `%install` each time.

4. **Limited GPU access**: Swift doesn't have direct GPU access like CUDA in Python. Use PythonKit to call TensorFlow/PyTorch for GPU computation.

5. **Code completion**: Currently not fully working (under investigation)

## Troubleshooting

### Kernel not found after installation

**Solution**: Make sure you restarted the runtime after installation:
- Runtime → Restart runtime

### Import errors with PythonKit

**Solution**: Make sure `%install` was in the **first cell** and ran successfully:

```swift
%install '.package(url: "https://github.com/pvieito/PythonKit", branch: "master")' PythonKit
```

### matplotlib plots not showing

**Solution**: Make sure you enabled inline matplotlib:

```swift
IPythonDisplay.shell.enable_matplotlib("inline")
```

### Python library not found (numpy, pandas, etc.)

**Solution**: Install the Python library first:

```bash
!pip install numpy pandas matplotlib scikit-learn
```

Then import with PythonKit:

```swift
let np = Python.import("numpy")
```

### Session disconnected / Out of memory

**Solution**: Colab has memory limits. If you're working with large datasets:

```swift
// Free memory explicitly
let largeArray = np.zeros([10000, 10000])
// ... use it ...
// Python.None is needed to free Python objects
```

### Runtime takes too long

**Solution**: The first `%install` for PythonKit takes ~10 minutes to compile. Be patient! Subsequent cells will be fast.

## Tips for Google Colab

### 1. Save Your Work

Colab notebooks are saved to Google Drive automatically, but packages are not persistent. Always include `%install` cells in your notebooks.

### 2. Use Python for Heavy Computation

For computation-heavy tasks (deep learning, large datasets), use Python/TensorFlow and call from Swift via PythonKit:

```swift
import PythonKit

let tf = Python.import("tensorflow")
let model = tf.keras.models.Sequential([
    tf.keras.layers.Dense(128, activation: "relu"),
    tf.keras.layers.Dense(10, activation: "softmax")
])

// Use Swift for logic, Python for heavy lifting
```

### 3. Combine Swift and Python Strengths

- **Use Swift for**: Type safety, clean code structure, algorithms
- **Use Python (via PythonKit) for**: Data science libraries, ML frameworks, visualization

### 4. Check Available Memory

```python
# In a Python cell
!free -h
```

### 5. Install Additional Swift Packages

Explore Swift packages at [Swift Package Index](https://swiftpackageindex.com):

```swift
// Example: Swift Algorithms
%install '.package(url: "https://github.com/apple/swift-algorithms", from: "1.0.0")' Algorithms

// Example: Swift Collections
%install '.package(url: "https://github.com/apple/swift-collections", from: "1.0.0")' Collections
```

## Example Notebooks

After installation, you'll find a test notebook at:
- `/content/swift_test.ipynb` - Basic Swift features

## Resources

- [Swift Documentation](https://docs.swift.org)
- [PythonKit GitHub](https://github.com/pvieito/PythonKit)
- [Swift Package Index](https://swiftpackageindex.com)
- [matplotlib Documentation](https://matplotlib.org)
- [pandas Documentation](https://pandas.pydata.org)
- [NumPy Documentation](https://numpy.org)

## Getting Help

If you encounter issues:

1. Check this guide's Troubleshooting section
2. Review [PYTHONKIT_SETUP.md](PYTHONKIT_SETUP.md) for PythonKit details
3. Check [MATPLOTLIB_STATUS.md](MATPLOTLIB_STATUS.md) for plotting issues
4. Open an issue on GitHub with:
   - Error message
   - Steps to reproduce
   - Colab notebook link (if possible)

## Next Steps

- Try the complete example notebook above
- Explore Swift Package Index for useful packages
- Combine Swift's type safety with Python's data science ecosystem
- Share your Swift notebooks!

---

**Note**: This installation script downloads Swift 6.3 Development Snapshot (October 10, 2024) which is approximately 600MB. Make sure you have a stable internet connection.
