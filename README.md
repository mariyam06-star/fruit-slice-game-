🍉 Hand Fruit Slice Game

A Python-based fruit-slicing game that uses hand tracking to control the slicing action. The project runs inside a Python virtual environment and is designed to be developed and executed using VS Code on Windows.

📁 Project Location
C:\Users\ratho\OneDrive\Documents\Desktop\fruit-slice-game

🛠️ Requirements

Before running the project, make sure you have:

Windows
VS Code
Python 3.12.x
PowerShell
A webcam/camera
The project files
requirements.txt

Important: Python 3.12 is recommended for this project. If you currently have Python 3.13, create the virtual environment using Python 3.12.

1. Check Installed Python Versions

Open the VS Code terminal and run:

py --list


You may see something similar to:

 -V:3.13 *        Python 3.13


If Python 3.12 is not listed, install it using the steps below.

2. Install Python 3.12

The easiest method on Windows is:

winget install Python.Python.3.12


Wait for the installation to finish.

After installation, close VS Code completely and reopen it.

3. Verify Python 3.12

Open a new VS Code terminal and run:

py -3.12 --version


You should see:

Python 3.12.x


For example:

Python 3.12.10

4. Open the Project

Open VS Code and open the fruit-slice-game folder.

Alternatively, open PowerShell and run:

cd "C:\Users\ratho\OneDrive\Documents\Desktop\fruit-slice-game"


Your terminal should show:

PS C:\Users\ratho\OneDrive\Documents\Desktop\fruit-slice-game>

5. Create the Virtual Environment

Create a virtual environment using Python 3.12:

py -3.12 -m venv venv


After it finishes, check that the virtual environment was created:

dir venv


You should see folders such as:

Include
Lib
Scripts

6. Activate the Virtual Environment

PowerShell may prevent scripts from running by default.

First run:

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass


Then activate the virtual environment:

.\venv\Scripts\Activate.ps1


If successful, your terminal prompt should change to:

(venv) PS C:\Users\ratho\OneDrive\Documents\Desktop\fruit-slice-game>


The (venv) confirms that the virtual environment is active.

7. Install Dependencies

With the virtual environment activated, install the packages listed in requirements.txt:

python -m pip install -r requirements.txt


Wait until the installation completes successfully.

You can also update pip if necessary:

python -m pip install --upgrade pip


Then run:

python -m pip install -r requirements.txt

8. Run the Game

After installing the dependencies, run:

python hand_fruit_slice.py


The game should start.

Make sure your webcam is connected and available, since the hand-tracking functionality requires camera input.

🚀 Quick Start

Once Python 3.12 and the virtual environment have already been configured, you only need:

cd "C:\Users\ratho\OneDrive\Documents\Desktop\fruit-slice-game"

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

.\venv\Scripts\Activate.ps1

python hand_fruit_slice.py

🧑‍💻 VS Code Workflow

The recommended workflow is:

Open VS Code
     ↓
Open fruit-slice-game
     ↓
Open Terminal
     ↓
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
     ↓
.\venv\Scripts\Activate.ps1
     ↓
python hand_fruit_slice.py

❗ Troubleshooting
Python 3.12 is not found

Run:

py --list


If Python 3.12 is missing, install it:

winget install Python.Python.3.12


Then restart VS Code and verify:

py -3.12 --version

Activate.ps1 cannot be executed

Run:

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass


Then:

.\venv\Scripts\Activate.ps1


This changes the execution policy only for the current PowerShell process.

venv does not exist

Create it again using:

py -3.12 -m venv venv


Then activate it:

.\venv\Scripts\Activate.ps1

Dependencies are missing

Make sure the virtual environment is active:

(venv) PS C:\Users\ratho\OneDrive\Documents\Desktop\fruit-slice-game>


Then run:

python -m pip install -r requirements.txt

The game does not start

Check that:

Python 3.12 is being used.
The venv environment is activated.
requirements.txt was installed successfully.
hand_fruit_slice.py exists in the project folder.
Your webcam is connected and accessible.
VS Code is opened in the correct project directory.

You can verify the Python version inside the virtual environment with:

python --version


It should report Python 3.12.x.

📂 Expected Project Structure

Your project should look approximately like this:

fruit-slice-game/
│
├── venv/
│   ├── Include/
│   ├── Lib/
│   └── Scripts/
│
├── hand_fruit_slice.py
├── requirements.txt
└── README.md


Additional game assets or Python files may also be present depending on the project.

🎮 Running the Project

Every time you open a new terminal, activate the virtual environment before running the game:

.\venv\Scripts\Activate.ps1


Then:

python hand_fruit_slice.py

📌 If Python 3.12 Installation Fails

First check the installed Python versions:

py --list


If Python 3.12 is still unavailable, install Python 3.12 manually and then verify:

py -3.12 --version


Once Python 3.12 is available, recreate the environment:

cd "C:\Users\ratho\OneDrive\Documents\Desktop\fruit-slice-game"

py -3.12 -m venv venv

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

.\venv\Scripts\Activate.ps1

python -m pip install -r requirements.txt

python hand_fruit_slice.py

📄 License

Add your project's license information here if applicable.
