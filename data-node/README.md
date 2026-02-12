# Dataportal Node - Example Deployment

The general data node documentation can be found [here](https://medizininformatik-initiative.github.io/dataportal/data-node/overview.html).

For the example deployment keep reading below.

# The Data Node

The Data Node part of this repository provides a site (data integration center) with all the necessary components to set up in order to allow feasibility and data queries from the central data portal.

It inlcudes multiple interconnected services required to run a FDPG DUP project. 
It does not include the DSF Middleware component, which is required to communicate with the FDPG central portal.


## Overview

The Example Data Node is composed of the following services

- Blaze Patient Data (fhir-server)
- Blaze Terminology (terminology-server)
- FDE
- FLARE
- aether
- TORCH
- fhir-pseudonymizer
- fhir-flattener

For more detail on each service see the dataportal [documentation](https://medizininformatik-initiative.github.io/dataportal/data-node/overview.html#data-node-services)

Additionally it provides a bundled reverse proxy for easier installation:

- reverse proxy (rev-proxy)

The reverse proxy allows for integration into a site's multi-server infrastructure. It also provides basic auth capability for FHIR server and FLARE components.

### CQL Support

[CQL](https://cql.hl7.org) is supported. If your FHIR server **does not** support CQL itself then the FLARE component must be used as a kind of translation mediator.


## Setting up the Example Data Node

### Step 1 - Installation Docker

The installation of the Data Node requires Docker (https://docs.docker.com/engine/install/ubuntu/) and docker-compose (https://docs.docker.com/compose/install/).
If not already installed on your VM, install using the links provided above.

### Step 2 - Clone this Repository to your virtual machine

ssh to your virtual machine and switch to sudo `sudo -s`.
Designate a folder for your setup in which to clone the deploy repository, we suggest /opt (`cd /opt`)
Navigate to the directory and clone this repository: `git clone https://github.com/medizininformatik-initiative/dataportal.git`
Navigate to the data-node folder of the repository: `cd /opt/dataportal/data-node`
Checkout the version (git tag) of the data-node you would like to install: `git checkout <your-tag-name-here>`

### Step 3 - Initialise .env files

The data node requires .env files for the docker-compose setup. If you are performing a new setup of the project, execute the `initialise-node-env-files.sh`.

If you have set up the portal before compare the `.env` to the `.env.default` env files of each component and copy the additional params as appropriate.

### Step 4 - Set Up basic auth
To set up basic auth you can execute the `setup-base-auth.sh <username> <password>` to add a simple .htpasswd to protect your FHIR Server and FLARE component with basic authentication.
This creates a .htpasswd file in the `auth` directory, which will be mounted to the nginx, which is part of this deployment repository.

### Step 5 - Set Up ssl certificates

The example setup allows you to run the services under different subdomains or on one with context path.

Running this setup safely at your site requires a valid certificate and domains. Please contact the responsible body of your institution to receive both domains and a certificate containing these domains as subject alternative names (SAN). 

If you are running the data node in the context path mode you only need one domain certificate (e.g. my-diz.fdpg.data-node.de)

If you are running the data node in subdomain mode the following services require a domain each:

- Blaze FHIR server for patient data
- Blaze terminology server
- FLARE
- TORCH
- fhir-pseudonymizer
- fhir-flattener
- Keycloak (optional, see step 8)

You will require two .pem files: a `cert.pem` (certificate) and `cert.key` (private key).

Once you have the appropriate certificates you should save them under `/opt/dataportal/data-node/auth`.
Set the rights for all files of the auth folder to 655 `chmod 655 /opt/dataportal/data-node/auth/*`.

- If you do not provide a cert.pem and cert.key file the reverse proxy will not start up, as it will not be able to provide a secure https connection.
- The rest of the data node will still work, as it does create a connection to the localhost without the need to make itself accessible.
- However, if you would like to for example load data into the FHIR server from an ETL job on another VM you will need to expose the FHIR server via a reverse proxy, which will require the certificates above.

### Step 6 - Create trust store for blaze

Generate a PKCS12 certificate file `./auth/trust-store.p12` containing the `cert.pem`
(see step 5 above). Running the script [generate-cert.sh](./generate-cert.sh) will generate the PKCS12
certificate file (and a self-signed `cert.pem` and `cert.key`, if these don't exist).

### Step 7 - Configure your data node

> [!NOTE]
> All user env variables should be changed and all PASSWORD and SECRET variables should be set to secure passwords.

To configure the DSF middleware to connect to the node and the central dataportal follow the [DSF configuration wiki][1].

You need to configure the domains/hostnames in all env variables for the access from outside and for the OpenID Connect Provider
used for OAuth authentication against the BLAZE patient data FHIR server, which is needed for logging into the BLAZE frontend. The domains/hostnames correspond to the domain(s) covered by the ssl certificate you received in step 5.

For the reverse proxy you need to choose the configuration (variable `DATA_NODE_REV_PROXY_NGINX_CONFIG` in
[rev-proxy/.env](./rev-proxy/.env)) which also decides what the changes to the `.env` files are you have to make:

- [./subdomains.nginx.conf](./rev-proxy/subdomains.nginx.conf) with separate domains for the services (fhir-server (incl) and optionally flare and keycloak)
  - All subdomains must point to the host machine the triangle will run on.
  - Set the service hostnames (`FLARE_HOSTNAME`, `FHIR_HOSTNAME`, `TORCH_HOSTNAME` and `KEYCLOAK_HOSTNAME`, depending on which services you need) in [rev-proxy/.env](./rev-proxy/.env).
  - You can change the default external port the reverse proxy listens on in [rev-proxy/.env](./rev-proxy/.env) (variable `DATA_NODE_REV_PROXY_PORT`).
    Any value other than `443` needs to be added to all external url's in the `.env` files and to the url's used for accessing the triangle from outside.
    The default value is `444` to avoid a conflict with the proxy of the local data portal when it is deployed on the same host.
  - Change the following variables in [fhir-server/.env](./fhir-server/.env):
    - `FHIR_SERVER_FRONTEND_KEYCLOAK_ENABLED`:
      - Set to `true` if you want to use the bundled keycloak.
        - `FHIR_SERVER_KC_HOSTNAME_URL`: set the domain part to the value you set for `KEYCLOAK_HOSTNAME` before and the port to the `REV_PROXY_PORT` set in [rev-proxy/.env](./rev-proxy/.env) (default `444`).
          The path must be set to `/` at the end of the url.
          For example, `https://auth.example.org:444/`.
        - `FHIR_SERVER_KC_HTTP_RELATIVE_PATH`: set to `/`.
      - Set to `false` to use none or your existing OpenID Connect provider.
    - `FHIR_SERVER_FRONTEND_ORIGIN`: set the domain part to the value you set for `FHIR_HOSTNAME` before and the port to the `REV_PROXY_PORT` set in [rev-proxy/.env](./rev-proxy/.env) (default `444`).
      For example, `https://fhir.example.org:444`.
  - Change the values for the variables `FLARE_FHIR_OAUTH_ISSUER_URI` in [flare/.env](./flare/.env) and `FHIR_SERVER_OPENID_PROVIDER_URL` in [fhir-server/.env](./fhir-server/.env)
    to the issuer url of your OpenID Connect provider.
    - When using the bundled keycloak replace the values with `https://KEYCLOAK_HOSTNAME:REV_PROXY_PORT/realms/blaze`
      where `KEYCLOAK_HOSTNAME` is the domain you set before and `REV_PROXY_PORT` is the port number set in [rev-proxy/.env](./rev-proxy/.env) (default `444`).
    - When using your own OpenID Connect provider replace the values the corresponding issuer url.
- [./context-paths.nginx.conf](./rev-proxy/subdomains.nginx.conf) which requires only one domain/hostname and uses context paths (`/` for flare,`/fhir` for fhir-server
  - The domain must point to the host machine the triangle will run on.
  - Change the following variables in [fhir-server/.env](./fhir-server/.env):
    - `FHIR_SERVER_FRONTEND_KEYCLOAK_ENABLED`:
      - Set to `true` if you want to use the bundled keycloak.
        - `FHIR_SERVER_KC_HOSTNAME_URL`: set the domain part to the value you set for `KEYCLOAK_HOSTNAME` before and the port to the `REV_PROXY_PORT` set in [rev-proxy/.env](./rev-proxy/.env) (default `444`).
          The path must be set to `/auth` at the end of the url.
          For example, `https://example.org:444/auth`.
        - `FHIR_SERVER_KC_HTTP_RELATIVE_PATH`: set to `/auth`.
      - Set to `false` to use none or your existing OpenID Connect provider.
    - `FHIR_SERVER_FRONTEND_ORIGIN`: set the domain part to your domain/hostname and the port to the `REV_PROXY_PORT` set in [rev-proxy/.env](./rev-proxy/.env) (default `444`).
      For example, `https://example.org:444`.
  - Change the values for the variables `FLARE_FHIR_OAUTH_ISSUER_URI` in [flare/.env](./flare/.env) and `FHIR_SERVER_OPENID_PROVIDER_URL` in [fhir-server/.env](./fhir-server/.env)
    to the issuer url of your OpenID Connect provider.
    - When using the bundled keycloak replace the values with `https://KEYCLOAK_HOSTNAME:REV_PROXY_PORT/auth/realms/blaze`
      where `KEYCLOAK_HOSTNAME` is your domain and `REV_PROXY_PORT` is the port number set in [rev-proxy/.env](./rev-proxy/.env) (default `444`).
      For example, `https://example.org:444/auth/realms/blaze`.
    - When using your own OpenID Connect provider replace the values with the corresponding issuer url.


> [!WARNING]
> The variable `FHIR_SERVER_BASE_URL=http://fhir-server:8080`should be kept as is for the standard setup, so that the UI can
> correctly access the blaze fhir server.

The node is configured by default to start the following services, each of which can be disabled by setting the following variables in the
respectice env files of the service to `false`:

|Service|Folder|Enabling env var|
|--|--|--|
|Blaze Patient data|fhir-server|FHIR_SERVER_FRONTEND_KEYCLOAK_ENABLED|
|Keycloak Blaze|fhir-server|FHIR_SERVER_FRONTEND_KEYCLOAK_ENABLED|
|Blaze Terminology|terminology-server|TERMINOLOGY_SERVER_ENABLED|
|FLARE|flare|FLARE_ENABLED|
|TORCH|torch|TORCH_ENABLED|
|fhir-pseudonymizer|fhir-pseudonymizer|DIMP_ENABLED|
|fhir-flattener|fhir-flattener|FLATTENING_ENABLED|

The bundled keycloak service is enabled by default and is preconfigured, so you only need to change passwords and
secrets in `/opt/dataportal/data-node/fhir-server/.env` before starting the service.

If you want to use your own OpenID Connect provider you will need to set the correct issuer url and client credentials
in and disable the bundled keycloak service by setting environment variable `FHIR_SERVER_FRONTEND_KEYCLOAK_ENABLED`
to `false` in `/opt/dataportal/data-node/fhir-server/.env`.

### Step 8 - Start the data node

To start the triangle execute `/opt/dataportal/data-node/start-node.sh`.

This starts all node services unless say have been disabled in step 7.


### Step 9 - Configure keycloak to create a user account in the realm blaze

> [!NOTE]
> The keycloak provided here is an example setup, and we strongly recommend for each site to adjust the keycloak installation to their local security requirements or connect the local data node to a keycloak already provided at the site.

 Navigate to the keycloak administration url which is the value of the variable `FHIR_SERVER_FRONTEND_KEYCLOAK_HOSTNAME_URL` in
[fhir-server/.env](./fhir-server/.env) (e.g. `https://auth.example.org:444/` or `https://example.org:444/auth` depending
on the nginx configuration used) and log into keycloak using the user `admin` and password set by the variable
`FHIR_SERVER_FRONTEND_KEYCLOAK_ADMIN_PASSWORD` in [fhir-server/.env](./fhir-server/.env). Both variables had to be setup
in step 7.

1. Set the domain for your client: Switch to the realm `blaze` (realm name might be different if you use your own keycloak) by using the realm changer on top of the left navigation bar (should be set to master when logging in).
2. Add a user for your realm `blaze`: Click on Users > Create new user and fill in the field Username with a username of your choice. Click on Credentials > Set Password and fill the Password and Password Confirmation fields with a password of your choice and save the changes by clicking set password.

### Step 10 - Access the Node

In the default configuration, and given that you have set up a SSL certificate in step 4, the setup will expose the following services:

These are the URLs for access to the webclients via nginx:

| Component                 | URL if subdomain                                                                   | URL if context path | User             | Password         |
|---------------------------|-----------------------------------------------------------------------|--------------|------------------|------------------|
| FHIR Server               | https://your-fhir-subdomain.your-domain:configured-port/fhir          | https://your-data-node-domain:configured-port/fhir/fhir             | chosen in step 3 | chosen in step 3 |
| Terminology Server        | https://your-terminology-subdomain.your-domain:configured-port/fhir   |   https://your-data-node-domain:configured-port/terminology/fhir           | chosen in step 3 | chosen in step 3 |
| Flare                     | https://your-flare-subdomain.your-domain:configured-port/             | https://your-data-node-domain:configured-port/flare             | chosen in step 3 | chosen in step 3 |
| TORCH                     | https://your-torch-subdomain.your-domain:configured-port/             |  https://your-data-node-domain:configured-port/torch             | chosen in step 3 | chosen in step 3 |
| Fhir Pseudonymizer (DIMP) | https://your-dimp-subdomain.your-domain:configured-port/fhir               | https://your-data-node-domain:configured-port/dimp/fhir              | chosen in step 3 | chosen in step 3 |
| Fhir Flattener            | https://your-flatten-subdomain.your-domain:configured-port/fhir            | https://your-data-node-domain:configured-port/flattener/fhir  | chosen in step 3 | chosen in step 3 |


> [!IMPORTANT]
> In order to access the frontend of the BLAZE FHIR Server you will need to use the keycloak user account in the realm
> `blaze` you created in step 9.

Accessible service via localhost:

| Component   | URL                              | Authentication Type | Notes                |
|-------------|----------------------------------|---------------------|----------------------|
| FHIR Server | <http://localhost:8081/fhir>     | Bearer Token        | Configured in step 8 |
| Terminology Server | <http://localhost:8082/fhir>     | Bearer Token        | Configured in step 8 |
| Flare       | <http://localhost:8084>          | None required       |                      |
| TORCH       | <http://localhost:8086>          | None required       |                      |
| fhir-pseudonymizer       | <http://localhost:8083/fhir>          | None required       |                      |
| fhir-flattener       | <http://localhost:8088/fhir>          | None required       |                      |

Please be aware that you will need to set up an ssh tunnel to your server and forward the respective ports if you would like to access the services on localhost without a password.

For example for the FHIR Server: ssh -L 8081:127.0.0.1:8081 your-username@your-server-ip


### Step 11 - Update your Blaze Search indices

If you are using the Blaze server provided in this repository check if new items have been added to the fhir-server/custom-search-parameters.json since your last update.
If new search parameters have been added follow the "fhir-server/README.md -> Re-indexing for new custom search parameters" section to update your FHIR server indices.

### Step 12 - Init Testdata (Optional)

To initialise testdata execute `get-mii-testdata.sh`. This will download MII core dataset compliant testdata from <https://github.com/medizininformatik-initiative/kerndatensatz-testdaten>,
unpack it and save it to the testdata folder of this repository.

You can then load the data into your FHIR Server using the `upload-testdata.sh` script. Before  executing the `upload-testdata.sh` if you're not using fhir.localhost set the `DATA_NODE_TESTDATA_UPLOAD_FHIR_BASE_URL` variable to your FHIR_SERVER_HOSTNAME. 

## Updating the Data Node

If you have already installed the data node and just want to update it, follow these steps:

### Step 1 - Stop your node

`cd /opt/dataportal/data-node && bash stop-node.sh`

### Step 2 - Update repository and check out new tag

`cd /opt/dataportal/data-node && git pull`
`git checkout <new-tag>`

### Step 3 - transfer the new env variables

Compare the .env and .env.default files for each component and add any new variables from the .env.default file to the .env file.
Keep the existing configuration as is.

### Step 4 - Update your ontology

**Note:** The ontology is now part of the FLARE image and will not have to be loaded manually.

### Step 5 - Start your data node

To start the node navigate to `/opt/dataportal/data-node` and
execute `bash start-node.sh`.

### Step 6 - Update your DSF

If you are using the DSF to connect to the central data portal, please follow the instructions in the [DSF configuration wiki][1].

### Step 7 - Log in to the central feasibility portal and test your connection

Ask for the Url of the central portal at the FDPG or check Confluence for the correct address.

Log in to the portal and send a request with the Inclusion Criterion chosen from the Inclusion criteria tree (folder sign under Inclusion Criteria)
"Person > PatientIn > Geschlecht: Female,Male"

and press "send".

Check your triangle DSF BPE App logs:
docker logs -f id-of-the-dsf-bpe-app-container

you should see output similar to:
```
Mar 29, 2023 12:59:57 PM feasibility.FeasibilityExecution doExecution
FINE: {"version":"http://to_be_decided.com/draft-1/schema#","display":"","inclusionCriteria":[[{"termCodes":[{"code":"263495000","system":"http://snomed.info/sct","display":"Geschlecht"}],"context":{"code":"Patient","system":"fdpg.mii.cds","version":"1.0.0","display":"Patient"},"valueFilter":{"selectedConcepts":[{"code":"female","display":"Female","system":"http://hl7.org/fhir/administrative-gender"},{"code":"male","display":"Male","system":"http://hl7.org/fhir/administrative-gender"}],"type":"concept"}}]]}
```

### Step 8 - Update your Blaze Search indices

If you are using the Blaze server provided in this repository check if new items have been added to the fhir-server/custom-search-parameters.json since your last update.
If new search parameters have been added follow the "fhir-server/README.md -> Re-indexing for new custom search parameters" section to update your FHIR server indices.


## Configuration

### External repository configurations

For information on how to configure each service/component - follow the links to the documentation in the data node [service overview page](https://medizininformatik-initiative.github.io/dataportal/data-node/overview.html#data-node-services)

### Example Repository specific configurations

[since-badge]: https://img.shields.io/badge/Since-v6.0.0-green

--- 

#### `FLATTENING_ENABLED`

![Since v6.0.0][since-badge]

**Component:** fhir-flattener 

**Description:** if set to true enables the fhir-flattener in the example deployment

**Default:** – true

---

#### `DIMP_ENABLED`

![Since v6.0.0][since-badge]

**Component:** fhir-pseudonymizer 

**Description:** if set to true enables the fhir-pseudonymizer and the vfps

**Default:** – true

---

#### `KEYCLOAK_ENABLED`

![Since v6.0.0][since-badge]

**Component:** fhir-server

**Description:** if set to true enables the fhir-server including frontend and keylcoak

**Default:** – true

---

#### `FLARE_ENABLED`

![Since v6.0.0][since-badge]

**Component:** flare

**Description:** if set to true enables the flare component

**Default:** – true

---

#### `TERMINOLOGY_SERVER_ENABLED`

![Since v6.0.0][since-badge]

**Component:** terminology-server

**Description:** if set to true enables the blaze terminology service

**Default:** – true

---

#### `TORCH_ENABLED`

![Since v6.0.0][since-badge]

**Component:** TORCH

**Description:** if set to true enables the TORCH service

**Default:** – true

---

#### `TORCH_DATA_VOLUME`

![Since v6.0.0][since-badge]

**Component:** TORCH

**Description:** configures the output data volume or local dir path where torch writes the output

**Default:** – ./output

---

#### `FHIR_SERVER_HOSTNAME`

![Since v6.0.0][since-badge]

**Component:** Reverse Proxy  
**Description:** Configures the FHIR server hostname  
**Default:** –  fhir.localhost

---

#### `KEYCLOAK_HOSTNAME`

![Since v6.0.0][since-badge]

**Component:** Reverse Proxy 
**Description:** Configures the Keycloak hostname  
**Default:** –  auth.localhost

---

#### `FLARE_HOSTNAME`

![Since v6.0.0][since-badge]

**Component:** Reverse Proxy 
**Description:** Configures the FLARE server hostname  
**Default:** –  flare.localhost

---

#### `TORCH_HOSTNAME`

![Since v6.0.0][since-badge]

**Component:** Reverse Proxy
**Description:** Configures the TORCH server hostname  
**Default:** –  torch.localhost

---

#### `TERMINOLOGY_SERVER_HOSTNAME`

![Since v6.0.0][since-badge]

**Component:** Reverse Proxy 
**Description:** Configures the terminology server hostname  
**Default:** –  terminology.localhost

---

#### `FHIR_PSEUDONYMIZER_HOSTNAME`

![Since v6.0.0][since-badge]

**Component:** Reverse Proxy  
**Description:** Configures the FHIR pseudonymizer hostname  
**Default:** –  dimp.localhost

---

#### `FHIR_FLATTENER_HOSTNAME`

![Since v6.0.0][since-badge]

**Component:** Reverse Proxy 
**Description:** Configures the FHIR flattener hostname  
**Default:** –  flattener.localhost

---

### Support for self-singed certificates

Depending on your setup you might need to use self-singed certificates and the tools will have to accept your CAs.
For the triangle self-singed certificates are currently supported for the PATH: BPE (DSF) -> FLARE -> FHIR SERVER.

#### BPE (DSF)

The DSF Feasibility Plugin supports self-signed certificates - please see [DSF configuration wiki][1]
for details.

#### FLARE

FLARE supports the use of self-signed certificates from your own CAs. On each startup FLARE will search through the folder /app/certs inside the container , add all found CA `*.pem` files to a java truststore and start FLARE with this truststore.

In order to add your own CA files, add your own CA `*.pem` files to the `/app/certs` folder of the container.

Using docker-compose mount a folder from your host (e.g.: `./certs`) to the `/app/certs` folder, add your `*.pem` files (one for each CA you would like to support) to the folder and ensure that they have the .pem extension.


[1]: https://github.com/medizininformatik-initiative/dataportal/wiki/DSF-Middleware-Setup
