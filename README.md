# F5 SSL Orchestrator Office 365 URL Update Script
A small Python utility to download and maintain the dynamic set of Office 365 URLs as data groups and custom URL categories on the F5 BIG-IP, for use with SSL Orchestrator.

[![Releases](https://img.shields.io/github/v/release/f5devcentral/sslo-o365-update.svg)](https://github.com/f5devcentral/sslo-o365-update/releases)

### Script version
7.2.1

### SSL Orchestrator version support
This utility works on BIG-IP 14.1 and above, SSL Orchestrator 5.x and above.

### How to install 
- Download the script onto the F5 BIG-IP:

  `curl -k https://raw.githubusercontent.com/f5devcentral/sslo-o365-update/7.2.1/sslo_o365_update.py -o sslo_o365_update.py`

- Run the script with one of the following install options:

  - `python sslo_o365_update.py --install`  -- this option installs with the default configuration.

  - `python sslo_o365_update.py --install --config <JSON string>`  -- this option installs with a configuration passed in via serialized JSON string. Any attributes not defined will take default values.

  - `python sslo_o365_update.py --install --configfile <JSON file>`  -- this option installs with a configuration passed in via JSON file. Any attributes not defined will take default values.  


### How to modify the configuration
- Initiate the `--install` process again with a new `--config` or `--configfile` argument.

  See the JSON configuration template below. Anything passed into --config or --configfile must be in the correct JSON format. For example, to change only the endpoint value:
  
  `--install --config '{"endpoint": "Worldwide"}'`
  
  To change the schedule frequency (periods):
  
  `--install --config '{"schedule":{"periods":"monthly"}}'`
  
  Antying not specifically defined will take the default values.


### How to uninstall
- Run the script with the `--uninstall` option. This will remove the configuration file and scheduler. The URL categories, datagroups, and working directory will remain.

- Run the script with the `--full_uninstall` option. This will remove the configurtion file, scheduler, working directory files, URL categories, and datagroups.

### How to force an update
- Run the script with the `--force` option, either during install to immediately force a URL fetch, or at any time.

  `python sslo_o365_update.py --install --force`
  <br />
  `python sslo_o365_update.py --force`

### Show the running configuration
- Run the script with the `--printconfig` option to display the running configuration.

### HA considerations
- Perform the install operations on both units in an HA environment and then sync. The script runs independently on each peer and will not trigger an out-of-sync indication when updates are made.

### Egress proxy considerations
- The script uses system outbound proxy settings (System : Configuration : Device : Upstream Proxy).

---

### The configuration environment
The installed script creates a working directory (default: /shared/o365), a configuration (iFile) json file, and scheduler. The configuration json file controls the various settings of the script.


***Endpoint** - Microsoft Web Service Customer endpoints (ENABLE ONLY ONE ENDPOINT). These are the set of URLs defined by customer endpoints as described here: https://docs.microsoft.com/en-us/office365/enterprise/urls-and-ip-address-ranges. Valid values are **"Worldwide"**, **"USGovDoD"**, **"USGovGCCHigh"**, **"China"**, **"Germany"**.*

    "endpoint": "Worldwide"


***O365 "Service Areas"** - O365 endpoints to consume, as described here: https://docs.microsoft.com/en-us/office365/enterprise/urls-and-ip-address-ranges. The "common" service area should remain enabled as it contains the bulk of the URLs.*

    "service_areas":{
        "common": True|False           -> Microsoft 365 Common and Office Online
        "exchange": True|False         -> Exchange Online  
        "sharepoint": True|False       -> SharePoint Online and OneDrive for Business
        "skype": True|False            -> Skype for Business and Microsoft Teams
    }


***Outputs** - O365 Record objects to create*    

    "outputs":{
        "url_categories": True|False   -> Create URL categories
        "url_datagroups": True|False   -> Create URL data groups
        "ip4_datagroups": True|False   -> Create IPv4 data groups
        "ip6_datagroups": True|False   -> Create IPv6 data groups
    }


***O365 Categories** - create a single URL data set, and/or separate data sets for O365 Optimize/Default/Allow categories. The categories and recommended actions for each is described here: https://docs.microsoft.com/en-us/microsoft-365/enterprise/microsoft-365-network-connectivity-principles?view=o365-worldwide#BKMK_Categories*

    "o365_categories":{                  
        "all": True|False              -> Create a single date set containing all URLs (all categories)
        "optimize: True|False          -> Create a data set containing O365 "Optimize" category URLs (note that the optimized URLs are in Exchange and "SharePoint service areas)
        "default": True|False          -> Create a data set containing O365 "Allow" category URLs
        "allow": True|False            -> Create a data set containing O365 "Default" category URLs
    }


***Required O365 endpoints to import** - O365 required endpoints or all endpoints. Importing all endpoints includes non-O365 URLs that one may not want to bypass (ex. www.youtube.com). It is recommended to leave this enabled/true (only download required URLs).*

    "only_required": True|False        -> false=import all URLs, true=Office 365 required only URLs


***Excluded URLs** - (URL pattern matching is supported). Provide URLs in list format - ex. ["m.facebook.com", ".itunes.apple.com", "bit.ly"]. Even with "only_required" enabled, some non-Microsoft URLs are still included, mostly Certificate Authorities. The default settings include the set of CA URLs to exclude, but additional URLs can be added to this list as required. The list supports "ends-with" pattern matching.*

    "excluded_urls": []


***Included URLs** - (URL must be exact match to URL as it exists in JSON record - pattern matching not supported). Provide URLs in list format - ex. ["foo.com", "bar.com"].*     

    "included_urls": [] 
   
   
***Excluded IPs** - (IP must be exact match to IP as it exists in JSON record - IP/CIDR mask cannot be modified). Provide IPs in list format - ex. ["191.234.140.0/22", "2620:1ec:a92::152/128"].*

    "excluded_ips": [] 

***System-level configuration settings***

    "system":{
        "log_level": 1                       -> 0 = no logging, 1 = normal logging, 2 = verbose logging
        "working_directory": "/shared/o365"  -> The working directory to install and run the script from
    }
   
***System-level configuration settings***

    "schedule":{
        "periods":"monthly"                  -> The period, "monthly" or "weekly" to run the script
        "run_date":1                         -> The day of the week for weekly (0-6 Sunday-Saturday), or day of the month for monthly (1-31) to run the script
        "run_time":"04:00"                   -> The 24-hour time to run the script (ex. "04:00")
        "start_date":""                      -> A month/day/Year formatted date string (ex. 3/29/2021) to begin running the script
        "start_time":""                      -> A 24-hour time to start running the script (on the start_date)
    }
   
---

**Default configuration**
```json
{
    "endpoint": "Worldwide",
    "service_areas": {
        "common": True,
        "exchange": True,
        "sharepoint": True,
        "skype": True
    },
    "outputs": {
        "url_categories": True,
        "url_datagroups": True,
        "ip4_datagroups": True,
        "ip6_datagroups": True
    },
    "o365_categories": {
        "all": True,
        "optimize": True,
        "default": True,
        "allow": True
    },
    "only_required": True,
    "excluded_urls": [
        ".symcd.com",
        ".symcb.com",
        ".entrust.net",
        ".digicert.com",
        ".identrust.com",
        ".verisign.net",
        ".globalsign.net",
        ".globalsign.com",
        ".geotrust.com",
        ".omniroot.com",
        ".letsencrypt.org",
        ".public-trust.com",
        "platform.linkedin.com"
    ],
    "included_urls": [],
    "excluded_ips": [],
    "system": {
        "log_level": 1,
        "working_directory": "/shared/o365"
    },
    "schedule":{
        "periods":"monthly",
        "run_date":1,
        "run_time":"04:00",
        "start_date":"",
        "start_time":""
    }
}
```

---

**Improvements**
- Update 7.2.1 - to support additional enhancements
  - Updated to class-based Python script
  - Updated to support --config (serialized JSON string input) and --configfile (JSON file) install options
  - Updated to support --full_uninstall option to delete all configurations (local files, URL categories, datagroups)
  - Updated to support --printconfig option to show the running configuration (JSON)
  - Updated to support using system proxy settings (System : Configuration : Device : Upstream Proxy)
  - Updated to support /etc/cron.d/0hourly scheduler (replaces iCall periodic) for more granular m/d/Y HH:mm scheduling
  - Updated to support more comprehensive config input validation
