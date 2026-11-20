# CS302 Project — Questions 2, 3 and 4
## Group Members: M. Musab Ali Khan (24K-0528), Shahzaib Hasan (24K-0584), Zain Khan (24K-0509)

All project files are in this directory. Keep them together when copying the
project. Python 3.8 or newer is required. All Python imports use the standard
library or the Python files included here; no pip packages are required.

## Run the interface in VS Code

1. Open this entire folder in VS Code using **File → Open Folder**.
2. Open **Terminal → New Terminal**. The terminal should be in this folder.
3. Run:

   ```bash
   python3 run.py
   ```

   On Windows, use `py run.py`. If your system calls Python `python`, use
   `python run.py` instead.
4. Open <http://localhost:8000> in your browser. Keep the terminal running.
   Pick a dataset or upload a `.txt` file. This loads only the input.
   Press **Run walkthrough** to calculate it and start playback. Pause, step
   with the arrows, or drag the slider to inspect intermediate operations.
   The final answer and verification appear at the last step.
   Start with **Try 6 points** or **Try 18-digit numbers** for a short example.
5. Press **Ctrl+C** in the terminal to stop the server.

You can also open `run.py` and use **Run Python File in Terminal** with a Python
3 interpreter selected in VS Code. Running an algorithm module alone does not
start the interface. The HTML file needs the Python server; opening it directly
or serving it with Live Server does not provide the algorithm API.

If port 8000 is busy, run `python3 run.py 8001` and open
<http://localhost:8001>. The server listens on this computer only.

Paths are resolved from the script directory, so launching the scripts with
absolute paths also works from another working directory.

## Q2: regenerate datasets (optional)

```bash
python3 q2_generate_datasets.py
```

The 20 datasets and `q2_catalog.json` are already included. This command
recreates them in the same directory using fixed random seeds.
The algorithms are `q2_closest_pair.py` and `q2_karatsuba.py`.
The shared input parsers are in `q2_input.py`.

## Q3: print answers and timings

```bash
python3 q3_apply.py
```

Runs both algorithms against the included datasets. For datasets above 4,000
points, the check verifies the reported pair distance only; it does not
independently verify the minimum.

## Input format

Point files contain one `x y` pair per line, optionally preceded by an exact
point count. At least two finite points are required. Multiplication files
contain exactly two signed decimal integers, one per line. Blank lines are
ignored. Malformed input produces an error.

## Verification

```bash
python3 -m unittest -v test_submission
```

Checks the algorithms, parsers, API handlers and all included datasets.
An optional JavaScript syntax check, if Node.js is installed, is:

```bash
node --check q4_ui.js
```

Node.js is not required to run the project. The browser runs the JavaScript.


The walkthrough records operations from the actual Python algorithm run, then
plays them in the browser. Closest Pair shows splits, pair comparisons, strip
checks and returned results. Karatsuba shows operand splits, the three
subproducts, subtraction and recombination. Large intermediate integers are
abbreviated in explanations; the final product is complete. Operations below
recursion depth two and excess comparison steps are grouped, with their count
shown. Small examples use smaller base cases to make the recursion visible.

Optional UI behavior checks (requires Node.js, no npm packages):

```bash
node test_ui.js
```
