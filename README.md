# Dockerized Dash App Template


https://towardsdatascience.com/dockerize-your-dash-app-1e155dd1cea3


Basic Dash app with data load, global variable module, and various UI examples.

### NREL Branding
This app uses the NREL Branding component, which is included as a .tgz and is installed via pip (see below).


## How to run this app

(The following instructions apply to Windows command line.)

Create and activate a new virtual environment (recommended) by running
the following:

On Windows

```
virtualenv venv
\venv\scripts\activate
```
On Mac
```
virtualenv venv
source venv/bin/activate
```

Or if using linux

```bash
python3 -m venv myvenv
source myvenv/bin/activate
```

Install the requirements:

```
pip install -r dashboard/requirements.txt
```

Run the app:

```
python app.py
```
You can run the app on your browser at http://127.0.0.1:8050



## Resources

To learn more about Dash, please visit [documentation](https://plot.ly/dash).


## Docker

`docker build -t dash-app .`

`docker run dash-app`

## Docker Compose (recommended)

`docker compose -f docker-compose-dash-app.yml build`

`docker compose -f docker-compose-dash-app.yml up`
