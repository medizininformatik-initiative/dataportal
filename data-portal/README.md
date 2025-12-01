# Data Portal

The data portal provides a user interface with an appropriate backend for researchers to

1. Search a metadata catalog of criteria and data items
2. Define cohorts based on inclusion and exclusion criteria
3. Execute feasibility queries based on the cohort definitions
4. Define a Data Extraction


## Setting up the Data Portal - Local Installation

### Step 1 - Installation Docker

The installation of the Data Portal requires Docker (https://docs.docker.com/engine/install/ubuntu/) and docker-compose (https://docs.docker.com/compose/install/).
If not already installed on your VM, install using the links provided above.

### Step 2 - Clone this Repository to your virtual machine

ssh to your virtual machine and switch to sudo `sudo -s`.
Designate a folder for your setup in which you clone the deploy repository, we suggest /opt (`cd /opt`)
Navigate to the directory and clone this repository: `git clone https://github.com/medizininformatik-initiative/dataportal.git`
Navigate to the data-portal folder of the repository: `cd /opt/dataportal/data-portal`
Checkout the version (git tag) of the data portal you would like to install: `git checkout <your-tag-name-here>`

### Step 3 - Initialise .env files

The dataportal portal requires .env files for the docker-compose setup. If you are performing a new setup of the project, execute the `initialise-portal-env-files.sh`.

If you have set up the portal before, compare the .env to the .env.default env files of each component and copy the additional params as appropriate.

### Step 4 - Set up SSL certificates

Running this setup safely at your site requires a valid certificate and domain. Please contact the responsible body of your institution to receive both a domain and certificate.
You will require two .pem files: a cert.pem (certificate) and key.pem (private key).

Once you have the appropriate certificates you should save them under `/opt/dataportal/data-portal/auth`.
Set the rights for all files of the auth folder to 655 `chmod 655 /opt/dataportal/data-portal/auth/*`.

- Not providing the certificate files is not an option.

### Step 5 - Configure your data portal

If you use the default local data portal setup you will only have to change the following environment variables:

| file                   | environment variable                         | value for local setup                                              |
|------------------------|----------------------------------------------|--------------------------------------------------------------------|
| keycloak/.env          | KC_HOSTNAME                                  | base-url-of-your-local-data-portal-keycloak                        |
| keycloak/.env          | KC_HOSTNAME_ADMIN                            | base-url-of-your-local-data-portal-keycloak                        |
| keycloak/.env          | KC_ADMIN_USER                                | keycloak admin user name                                           |
| keycloak/.env          | KC_ADMIN_PW                                  | choose a secure password here e.g. Ykc2PINWatNqL5Wq,OIxFz1Sv3dzmQ2 |
| backend/.env           | BROKER_CLIENT_DIRECT_ENABLED                 | true                                                               |
| backend/.env           | API_BASE_URL                                 | base-url-of-your-local-data-portal-backend                         |
| backend/.env           | FLARE_WEBSERVICE_BASE_URL                    | http://flare:8080                                                  |
| backend/.env           | ALLOWED_ORIGINS                              | base-url-of-your-local-data-portal-backend                         |
| backend/.env           | KEYCLOAK_BASE_URL_ISSUER                     | base-url-of-your-local-data-portal-keycloak                        |
| gui/deploy-config.json | uiBackendApi > baseUrl                       | base-url-of-your-local-data-portal-backend/api/v3                  |
| gui/deploy-config.json | auth > baseUrl                               | base-url-of-your-local-data-portal-keycloak                        |
| proxy/.env.default	   | BACKEND_HOSTNAME                             | hostname (inkl. subdomain) of the local backend                    |
| proxy/.env.default     | KEYCLOAK_HOSTNAM                             | hostname (inkl. subdomain) of the local keycloak                   |
| proxy/.env.default     | GUI_HOSTNAME                                 | hostname (inkl. subdomain) of the local ui                         |

Please note that all user env variables (variables containing USER) should be changed and all password variables (variables containing PASSWORD or PW) should be set to secure passwords.

To configure domain proxies, change the hostnames in the following environment variables in the file `/opt/dataportal/data-portal/proxy/.env.default` according to the domains you possess.

The portal is configured by default to start the following services:

- Backend
- UI
- Keycloak

For the reverse proxy you need to choose the configuration (variable `DATA_PORTAL_PROXY_NGINX_CONFIG` in
[proxy/.env](./proxy/.env)) which also decides what the changes to the `.env` files you have to make:

- [./subdomains.nginx.conf](./proxy/subdomains.nginx.conf) with separate domains for the services (Backend, UI, Keycloak)
  - All subdomains must point to the host machine the portal will run.

  - Set the service hostnames (`BACKEND_HOSTNAME`, `KEYCLOAK_HOSTNAME` and `GUI_HOSTNAME`, depending on which services you need) in [proxy/.env](./proxy/.env).
- Change the following variables in [keycloak/.env](./keycloak /.env):
      - `KC_HOSTNAME`and `KC_HOSTNAME_ADMIN`: set the domain part to the value you set for `KEYCLOAK_HOSTNAME` before.
      -` KC_HTTP_RELATIVE_PATH`: set to `/auth`.
- Change the values for the variables `API_BASE_URL` in [backend/.env](./backend/.env) and `ALLOWED_ORIGINS` in [backend /.env](./backend/.env)
          to the base url of your data portal backend. In the [backend/.env](./backend/.env) change the values for the variable `KEYCLOAK_BASE_URL_ISSUER`	to the base url of your data portal keycloak.
- Change the following variables in [gui/deploy-config.json](./gui/deploy-config.json):
      - `uiBackendApi > baseUrl`: set the domain part of the local data portal backend.
      -  `auth > baseUrl`: set the domain part of the local data portal keycloak.
- On the [proxy/.env] use this variable `DATA_PORTAL_PROXY_NGINX_CONFIG=./subdomains.nginx.conf`.

- [./context-paths.nginx.conf](./proxy/context-paths.nginx.conf) which requires only one domain and uses context paths (`/auth` for keycloak,`/api` for backend and `/`) for user interface.
- The domain must point to the host machine the portal will run.
- On the [proxy/.env] use this variable`DATA_PORTAL_PROXY_NGINX_CONFIG=./context-paths.nginx.conf`
-  Change the following variable `KC_HOSTNAME` and `KC_HOSTNAME_ADMIN` in [keycloak/.env]: set the domain part of your domain. The path must be set to /auth at the end of the url. For example, https://example.org/auth.
- Add `/auth` in the following variable `KC_HTTP_RELATIVE_PATH` in [keycloak/.env]
- Change the following variable `API_BASE_URL` in [backend/.env]: set the domain part of your domain. The path must be set to /api at the end of the url. For example, https://example.org/api.
- Change the following variable `ALLOWED_ORIGINS`  in [backend/.env]: set the domain part of your domain. For example, https://example.org.
- Change the following variable`KEYCLOAK_BASE_URL_ISSUER` in [backend/.env]: set the domain part of your domain. The path must be set to /api at the end of the url. For example, https://example.org/auth.
- Add `/auth` in the following variable `KEYCLOAK_BASE_URL_JWK` in [backend/.env]
- Change the variable `BROKER_CLIENT_DIRECT_AUTH_OAUTH_ISSUER_URL` when using the bundled keycloak in [backend/.env]replace the values with https://DOMAIN:REV_PROXY_PORT/auth/realms/blaze where DOMAIN is your domain and REV_PROXY_PORT is the port number set in rev-proxy/.env (default 444). For example, https://example.org:444/auth/realms/blaze.
- On the [gui/deploy-config.json] change the following variables:
  - `uiBackendApi > baseUrl`: set the domain part of the local data portal backend with the context path `/api`. For example https://example.org/api.
  -  `auth > baseUrl`: set the domain part of the local data portal keycloak the context path `/auth`. For example https://example.org/auth.

In case you do **not** have a docker-wide configuration of your organizations proxy server(s) you might need to add the following parameters to the `environment` section of the `init-elasticsearch` service in `backend/docker-compose.yml`: `HTTP_PROXY`, `HTTPS_PROXY` and `NO_PROXY`. The first two should obviously be your proxy server, the last one must include `dataportal-elastic`.

Please note that the keycloak provided here is an example setup, and we strongly recommend for each site to adjust the keycloak installation to their local security requirements or connect the local data portal to a keycloak already provided at the site.

For more details on the environment variables see the paragraph **Configurable environment variables** of this README.

### Step 6 - Start the data portal

To start the portal navigate to `/opt/dataportal/data-portal` and
execute `bash start-portal.sh`.

This starts the following default local data portal, with the following components:

| Component | url                                                    | description |
|-----------|--------------------------------------------------------|-------------|
| GUI       | https://data-portal-subdomain.my-data-portal-domain    |             |
| Keycloak  | https://keycloak-subdomain.my-data-portal-domain      |             |
| Backend   | https://backend-subdomain.my-data-portal-domain/api/v5 |             |


### Step 7 - Configure keycloak and add a user for the user interface

Please note that the keycloak provided here is an example setup, and we strongly recommend for each site to adjust the keycloak installation to their local security requirements or connect the local data portal to a keycloak already provided at the site.

Navigate to https://keycloak-subdomain.my-fesibility-domain/admin/master/console/
click on "Administration Console" and log in to keycloak using the admin user and password set in step 6 (`KC_BOOTSTRAP_ADMIN_USERNAME`, `KC_BOOTSTRAP_ADMIN_PASSWORD`).
User: admin
Pw: my password set in step 6

1. Set the domain for your client:
Switch to the `dataportal` realm (realm name might be different if you use your own keycloak) by using the realm changer on top of the left navigation bar (should be set to `master` when logging in)
Click on `Clients > dataportal` and change the fields: Root URL, Home URL and Web Origins
to: https://your-dataportal-domain

    and **Valid Redirect URIs** to: https://your-data-portal-domain/*

    and **Valid post logout redirect URIs** to: https://your-data-portal-domain/*

    and leave **Admin URL** empty

    Save the changes by clicking the "save" button.

2. Add a user for your data portal user interface:
Click on `Users > Create new user` and fill in the field **Username** with a username of your choice.
Click on **Credentials** > **Set Password** and fill the `Password` and `Password Confirmation` fields with a password of your choice and save the changes by clicking `set password`.
Click on ** Role Mapping > Assign Role **  , select DataportalUser and click `Assign`


### Step 8 - Access the user interface and send first query

Access your user interface under <https://your-data-portal-domain> and log in with the user created in step 8.

Click on **New query**, create a query and send it using the **send** button.
After a few moments you should see the results to your query in the **Number of patients** window.


## Updating your local data portal

If you have already installed the local data portal and just want to update it, follow these steps:


### Step 1 - Stop your portal

`cd /opt/dataportal/data-portal && bash stop-portal.sh`

### Step 2 - Update repository and check out new tag

`cd /opt/dataportal && git pull`
`git checkout <new-tag>`

### Step 3 - transfer the new env variables

Compare the .env and .env.default files for each component and add any new variables from the .env.default file to the .env file.
Keep the existing configuration as is.

### Step 4 - Start your portal

To start the portal navigate to `/opt/dataportal/data-portal` and
execute `bash start-portal.sh`.

### Step 5 - Log in to the local data portal and test your connection

Ask for the Url of the central portal at the FDPG or check Confluence for the correct address.

Log in to the portal and send a request with the Inclusion Criterion chosen from the Inclusion criteria tree (folder sign under Inclusion Criteria)
"Person > PatientIn > Geschlecht: Female,Male"

and press "send".

## Configuration

### External repository configurations

- For the backend configuration variables refer to the [backend repository](https://github.com/medizininformatik-initiative/feasibility-backend)
- For the ui configuration variables refer to the [ui repository](https://github.com/medizininformatik-initiative/feasibility-gui)
- For the keycloak configuration variables refer to the [keycloak documentation](https://www.keycloak.org/server/all-config)


### Example Repository specific configurations

[since-badge]: https://img.shields.io/badge/Since-v6.0.0-green

---

#### `BACKEND_HOSTNAME`
![Since v6.0.0][since-badge]

**Component:** Proxy 

**Description:** Hostname for the backend - if using subdomain deployment

**Default:** – api.datenportal.localhost

---

#### `KEYCLOAK_HOSTNAME`
![Since v6.0.0][since-badge]

**Component:** Proxy 

**Description:** Hostname for the keycloak auth - if using subdomain deployment

**Default:** – auth.datenportal.localhost

---

#### `UI_HOSTNAME`
![Since v6.0.0][since-badge]

**Component:** Proxy 

**Description:** Hostname for the user inteface - if using subdomain deployment

**Default:** – datenportal.localhost

---

#### `DATA_PORTAL_PROXY_NGINX_CONFIG`
![Since v6.0.0][since-badge]

**Component:** Proxy 

**Description:** Allows switching between subdomain `./subdomains.nginx.conf` and context path `./context-paths.nginx.conf` deployment 

**Default:** – ./subdomains.nginx.conf

---

#### `DATA_PORTAL_PROXY_CERTIFICATE_PATH`
![Since v6.0.0][since-badge]

**Component:** Proxy 

**Description:** path to cert.pem used for the proxy server certificate

**Default:** – "../auth/key.pem"

---

#### `DATA_PORTAL_PROXY_CERTIFICATE_KEY_PATH`
![Since v6.0.0][since-badge]

**Component:** Proxy 

**Description:** path to key.pem used for the proxy server certificate

**Default:** – "../auth/key.pem"

---

#### `KC_DB_URL_DB`
![Since v6.0.0][since-badge]

**Component:** Keycloak 

**Description:** database name of the keycloak db -> used for keycloak and the shipped postgresql db

**Default:** – keycloakdb

---

### Support for self-signed certificates

Depending on your setup you might need to use self-singed certificates and the tools will have to accept your CAs.
For the portal then only tool for which this is relevant is the backend.

#### Data Potal Backend

The Data Potal backend supports the use of self-signed certificates from your own CAs. On each startup, the data portal backend will search through the folder /app/certs inside the container, add all found CA *.pem files to a java truststore and start the application with this truststore.

Using docker-compose, mount a folder from your host (e.g.: ./certs) to the /app/certs folder, add your *.pem files (one for each CA you would like to support) to the folder and ensure that they have the .pem extension.

In this deployment repository we have prepared this for you. To add your own CA add the respective ca *.pem files to the backend/certs folder.
