tnrc-sp
=======

Module description
--------------------
It is 'tnrcsp' module (Transport Network Resource Controller - Specific Part).

TNRC Specific Part (TNRC-SP) component is a part of GMPLS+ controller and allows retrieval of information about the virtual transport resources (inventory, states, alarms)
and configuration of virtual transport resources. It performs all communication between NCP+ and Upper-LICL via CCI interface. The component prototype implements HTTP-REST clients
for virtual node inventory and virtual node cross-connection services offered by Upper-LICL element. Additionally, TNRC-SP component implements HTTPS server for virtual resource notification
coming from LICL layer to GMPLS+ controller via CCI interface. On the other hand, TNRC-SP component prototype implements CORBA servants and clients for communication with TNRC Abstract Part.
The prototype is implemented from scratch in Python v2.6 language.


Files in the module
--------------------
* tnrcpsp_main.py
    - main file of the module
* tnrcpsp.conf.sample
    - sample configuration for tnrcsp module
* restInterfaceCCI.py
    - HTTP REST implementation of CCI interface towards LICL
    - require wsgiservice (already included in psnc_geysers_utils library),
    - require python-webob and python-decorator libraries (to be installed by apt-get install)
    - require additionally python-werkzeug and python-openssl when module is configured to use SSL connections
* tnrcspCorbaInterface.py
    - corba interface servant towards tnrc-ap
    - require omniorbpy (requires http://omniorb.sourceforge.net/)
* tnrcsp_dm.py
    - internal methods of tnrcsp module
* configure
    - creates python Corba servant stubs and a configuration file
* restProxyInfo.py and xcInfo.py
    - supporting modules which exposes internal GMPLS+ controller information to external modules (VRM-SP element, demonstration PowerPoint slides, etc)

* idls/*
    - IDL files used to interact with TNRC-AP
    
* testing/corbaInterfaceTest.py
    - simple client generating Corba requests towards tnrcsp
    - require omniorb (requires http://omniorb.sourceforge.net/)
* testing/licl-stup.py
    - simulator of LICL CCI interface
    - require wsgiservice (already included in psnc_geysers_utils library),
    - require python-webob and python-decorator libraries (to be installed by apt-get install)
    - require additionally python-werkzeug and python-openssl when module is configured to use SSL connection
* testing/restInterfaceCCI.py
    - HTTP REST CCI implementation for licl-stup module
* testing/tnrcap-stup.py
    - simulator of TNRC-AP module
* testing/configure
    - configure licl-stup module
* testing/genericNode.py
    - script providing a template for producing licl-stub Virtual Infrastructure data
* testing/Pisa20Feb2012, testing/Colchester16Apr2012
    - Virtual Infrastructure data for various software integration events
* testing/tnrcpsp.conf.sample
    - sample configuration for licl-stup module


Most important requirements
------------------------------
1) Python libraries:
 - python-webob
 - python-decorator
 
2) Supporting library 'geysers_psnc_utils' from GEYSERS repository already installed


Basic installation
------------------
1) Please use:
  ./configure
  which is compiling python corba stub modules and create config file for 'tnrcsp' module
  
2) Edit module configuration in tnrsp.conf file (Follow 'TNRC-SP module configuration').


Advance installation
---------------------
1) In order to use SSL connection please use:
  ./ssl/create_ssl_certificate.sh
 which is creating SSL certificate and private key.
  

TNRC-SP module configuration
-------------------------------
For TNRC-SP all configuration is related to communication interfaces used by the module.
Commenting or deleting some part of configuration means that part of TNRC-SP functinality will be disabled.
The explanation of configuration parameters is presented in form of comments ('#') within a configuration file.

The content of 'tnrsp.conf' is the following:

<pre>
INTERFACES = {
    'clients': # contains configuration for used clients towards others modules
    {
        'rest-CCI': # configuration of client towards Upper-LICL CCI interface
        {
            'address':'localhost', # address of Upper-LICL CCI interface server
            'port': 8011, # port of Upper-LICL CCI interface server
            'nodeId': 1, # identifier of virtual node from VI which is to be controlled by GMPLS+ controller
            'ssl': False, # is SSL connection to be used
            'timeout': 10, # timeout for HTTP responses
        },
        'tnrcapConfig': # configuration of client towards TNRC-AP config interface
        {
            'iorName': '/opt/gmpls_ctrl_core/var/gmpls/tnrc_conf.ior', # location of IOR file
        },
        'tnrcapPresence': # configuration of client towards TNRC-AP presence interface
        {
            'iorName': '/opt/gmpls_ctrl_core/var/gmpls/tnrc_presence.ior', # location of IOR file
        },
        'tnrcapNotification': # configuration of client towards TNRC-AP notification interface
        {
            'iorName': '/opt/gmpls_ctrl_core/var/gmpls/tnrc_notif.ior', # location of IOR file
        },
        'LRM': # configuration of client towards LRM interface
        {
            'iorName': '/opt/gmpls_ctrl_core/var/gmpls/lrm.ior', # location of IOR file
        },
        
        #'AaiAuthentication': # configuration of client towards AAI service
        #{
        # 'iorName': '/tmp/AaiServer.ior', # location of IOR file
        # 'user': 'Canh', # user used for authentication over CCI
        # 'passwd': '123456', # passworld used for authentication over CCI
        #},
    },
    'servants': # contains configuration for services provided by TNRC-SP module
    {
        'rest-CCI': # configuration of TNRC-SP CCI service
        {
            'port': 8010, # port used by TNRC-SP CCI service
            'ssl': False, # is SSL used by TNRC-SP CCI service
            'certFilesDir':'/home/user/geysers-wp4/branches/python_modules/myModule/ssl/' # location of SSL certification files
        },
        'tnrcap': # configuration of TNRC-SP XC service
        {
            'timeout': 10, # timeout for handling of service requests within TNRC-SP module
        },
        'rest-Info': # configuration of INFO service required by VRM-SP module
        {
            'port:7010, # port used by INFO service
            'ssl': False, # is SSL used by INFO service
        },
        'xc-Info': # configuration of XC-INFO service required by demonstrations slides
        {
            'port:9090, # port used by XC-INFO service
            'ssl': False, # is SSL used by XC-INFO service
        },
    },
}
</pre>

Basic usage
-------------
  python tnrcsp_main.py start
  python tnrcsp_main.py stop
  python tnrcsp_main.py restop
  python tnrcsp_main.py --help

For basic usage files:
 - tnrcsp.log and tnrcsp.conf are located in tnrcsp module directory
 - tnrcsp.pid, tnrcsp_xc.ior and tnrcsp_conf.ior are stored in '/tmp


Advance usage example
-------------------------
Directory location of pidfile, logfile, iorfiles, configfile can be declared by attributes:

  python tnrcsp_main.py start --iorDir=/tmp --confDir=./ --logDir=/tmp --pidDir=/tmp
  python tnrcsp_main.py stop --iorDir=/tmp --confDir=./ --logDir=/tmp --pidDir=/tmp


Installation and execution within NCP+ Virtual Machine
------------------------------------------------------
1) Upload tnrcsp source code to:
   /opt/gmpls_ctrl_core/src/tnrc-sp
   There are already installed symbolic links for /opt/gmpls_ctrl_edge and /opt/gmpls_ctrl_border.
   
2) Follow 'Basic installation' (see above).

3) Edit module configuration in
     a) /opt/gmpls_ctrl_core/etc/tnrcsp.conf
     b) /opt/gmpls_ctrl_edge/etc/tnrcsp.conf
     c) /opt/gmpls_ctrl_border/etc/tnrcsp.conf
    depending on which kind of GMPLS+ controller will be deployed

4) Start, stop tnrcsp module standalone by:
     a) /opt/gmpls_ctrl_core/bin/gmpls-tnrcsp [start|stop]
     b) /opt/gmpls_ctrl_edge/bin/gmpls-tnrcsp [start|stop]
     c) /opt/gmpls_ctrl_border/bin/gmpls-tnrcsp [start|stop]
    depending on which kind of GMPLS+ controller is deployed
    
    
Usage of 'licl-stup' module
---------------------------
Configuration is done by:
  ./testing/configure
and editing licl-stub.conf file

Operation is done by:
  python licl-stub.py start
  python licl-stub.py stop
  python licl-stub.py restop
  python licl-stub.py --help

Example of advance usage is:
   python tnrcsp_main.py start --confDir=./ --logDir=/tmp --pidDir=/tmp
   python tnrcsp_main.py stop --confDir=./ --logDir=/tmp --pidDir=/tmp
   
   
Additional info
---------------
Implementation created in FP7-Geysers project.
