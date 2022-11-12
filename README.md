# The C-SEF web app
This repository houses the web app that implements the C-SEF mechanism for resource-constrained pooled testing for COVID-19. For more information, see [this arxiv paper](https://arxiv.org/abs/2206.10660). A version of this app was used for the C-SEF trial at the [Potosinian Institute for Scientific Research and Technology](https://www.ipicyt.edu.mx).

# Implementation details
The web app is implemented using the [Flask](https://flask.palletsprojects.com/en/2.2.x/) micro framework. Our implementation uses [Mosek](https://www.mosek.com) to solve the underlying conic programmes to allocate tests. Mosek is a commercial solver that offers free academic licences. The `flask-babel` package allows to painlessly translate the web app into any language of choice; a translation into Spanish is provided as an example.

# Credit
The web app was developed by a team at the <strong>University of Oxford</strong> and [The United Nations University - Maastricht Economic and Social Research Institute on Innovation and Technology](https://www.merit.unu.edu/). The lead developer is [Edwin Lock](www.edwinlock.com). Kat Molinet developed the scheduling preferences for participants as well as variable testing budgets across the days of the week. This includes the implementation of the weekly allocation algorithm. [Michelle Gonzalez Amador](https://m-gonzalezamador.com) lead frontend development, built the`flask-babel' Spanish dictionary, coordinated deployment of the web app during the IPICYT trial, and contributed to bug fixes and testing. [Simon Finster](https://www.simonfinster.com) contributed with adjustments of the allocation algorithm, frontend work, bug fixes and testing. 

# Installation
We give brief instructions to set up a Python virtual environment and install the required dependencies. This allows you to run the web app locally on your computer. Minimal experience with Python and the terminal is recommended. Contact <mail@edwinlock.com> if you have any issues.  If you wish to host this web app publicly, we have had good experiences with the hosting platform <https://www.pythonanywhere.com>.

## MacOS (and Linux)
These are brief instructions for macOS. They should also work for Linux systems.

1. Install Python 3.8 or newer.
2. Get the files from the GitHub server
```console
$ git clone https://github.com/edwinlock/csef.git
```
3. Install MOSEK according to instructions [here](https://www.mosek.com/documentation/).

    3.1 Please note that if you are working with MacOS with an M1 chip or above, you must download the BETA version (10.0), due to Darwin ARM incompatibility.
    You will also be required to quarantine the following file <strong> libtbb.12.dylib </strong>.For a discussion as to why, please follow this [thread](https://discuss.kotlinlang.org/t/macos-library-load-disallowed-by-system-policy/17567). 
    ```console
    $ sudo xattr -d com.apple.quarantine /Users/YourUserName/Documents/yourPath/csef/venv/lib/python3.10/site-packages/mosek/libtbb.12.dylib
    ```


4. Go to the project directory and set up a virtual environment (venv)
```console
$ cd csef
$ python -m venv venv
```
5. Activate virtual environment
```console
$ source venv/bin/activate
```
6. Install the dependencies
```console
$ pip install -r requirements.txt
```
7. Compile the translations
```console
$ pybabel compile -d webapp/translations
```
8. Run the app locally
```console
$ flask run
```
