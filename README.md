# F5 SSL Orchestrator Office 365 URL Update Script
A small Python utility to download and maintain the dynamic set of Office 365 URLs as data groups and custom URL categories on the F5 BIG-IP, for use with SSL Orchestrator.

[![Releases](https://img.shields.io/github/v/release/f5devcentral/sslo-o365-update.svg)](https://github.com/f5devcentral/sslo-o365-update/releases)

### Script version
7.3.0

### SSL Orchestrator version support
This utility works on BIG-IP 14.1 and above, SSL Orchestrator 5.x and above.



<details>
<summary><b>How to install</b></summary>
  
  - Download the script onto the F5 BIG-IP:

    `curl -k https://raw.githubusercontent.com/f5devcentral/sslo-o365-update/7.2.6/sslo_o365_update.py -o sslo_o365_update.py`

  - Run the script with one of the following install options. Note that the install options create or replace an existing configuration, but **will not** by itself initiate an O365 URL fetch. To force a fetch on install, include the `--force` option.

    - `python sslo_o365_update.py --install`  -- this option installs with the default configuration.

    - `python sslo_o365_update.py --install --config <JSON string>`  -- this option installs with a configuration passed in via serialized JSON string. Any attributes not defined will take default values.

    - `python sslo_o365_update.py --install --configfile <JSON file>`  -- this option installs with a configuration passed in via JSON file. Any attributes not defined will take default values.
  
</details>

  
  
<details>
<summary><b>How to modify the configuration</b></summary>
  
  - Initiate the `--install` process again with a new `--config` or `--configfile` argument.

    See the JSON configuration template below. Anything passed into --config or --configfile must be in the correct JSON format. For example, to change only the endpoint value:
  
    `--install --config '{"endpoint": "Worldwide"}'`
  
    To change the schedule frequency (periods):
  
    `--install --config '{"schedule":{"periods":"monthly"}}'`
  
    Anything not specifically defined will take the default values. See "default configuration" below.
  
</details>

  
  
<details>
<summary><b>How to force an update</b></summary>
  
  - Run the script with the `--force` option, either during install to immediately force a URL fetch, or at any time.

    `python sslo_o365_update.py --install --force`
  
    `python sslo_o365_update.py --force`
  
</details>  

  
  
<details>
<summary><b>How to show the running configuration</b></summary>
  
  - Run the script with the `--printconfig` option to display the running configuration.

    `python sslo_o365_update.py --printconfig`
  
</details>

  

<details>
<summary><b>How to uninstall</b></summary>
  
  - Run the script with the `--uninstall` option. This will remove the configuration file and scheduler. The URL categories, datagroups, and working directory will remain.

  - Run the script with the `--full_uninstall` option. This will remove the configurtion file, scheduler, working directory files, URL categories, and datagroups.
  
</details>


<details>
<summary><b>How to search the Office365 categories</b></summary>
  
  - Run the script with the `--search` option and add the full URL to search (ex. `--search https://smtp.office365.com`)
  
</details>
  
  
<details>
<summary><b>How to upgrade from previous version</b></summary>
  
  - Save the running config to a file:

    `python sslo_o365_update.py --printconfig > config.json`

  - Install the new version and point to the config file:

    `python sslo_o365_update_v7.2.7.py --install --configfile config.json`
  
</details>

  
  
<details>
<summary><b>HA considerations</b></summary>  
  
  - Perform the install operations on both units in an HA environment and then sync. The script runs independently on each peer and will not trigger an out-of-sync indication when updates are made.
  
</details>
  

<details>
<summary><b>Egress proxy considerations</b></summary>  
  
  - The script uses system outbound proxy settings (System : Configuration : Device : Upstream Proxy).
  
</details>
  
---

### The configuration environment
The installed script creates a working directory (default: /shared/o365), a configuration (iFile) json file, and scheduler. The configuration json file controls the various settings of the script.

<br />
  
**Endpoint** - Microsoft Web Service Customer endpoints (ENABLE ONLY ONE ENDPOINT). These are the set of URLs defined by customer endpoints as described here: https://docs.microsoft.com/en-us/office365/enterprise/urls-and-ip-address-ranges. Valid values are **"Worldwide"**, **"USGovDoD"**, **"USGovGCCHigh"**, **"China"**, **"Germany"**.

    "endpoint": "Worldwide"

<br />
  
**O365 "Service Areas"** - O365 endpoints to consume, as described here: https://docs.microsoft.com/en-us/office365/enterprise/urls-and-ip-address-ranges. The "common" service area should remain enabled as it contains the bulk of the URLs.

    "service_areas":{
        "common": True|False           -> Microsoft 365 Common and Office Online
        "exchange": True|False         -> Exchange Online  
        "sharepoint": True|False       -> SharePoint Online and OneDrive for Business
        "skype": True|False            -> Skype for Business and Microsoft Teams
    }

<br />
  
**Outputs** - O365 Record objects to create   

    "outputs":{
        "url_categories": True|False   -> Create URL categories
        "url_datagroups": True|False   -> Create URL data groups
        "ip_datagroups":  True|False   -> Create IPv4 data groups
    }

<br />
  
**O365 Categories** - create a single URL data set, and/or separate data sets for O365 Optimize/Default/Allow categories. The categories and recommended actions for each is described here: https://docs.microsoft.com/en-us/microsoft-365/enterprise/microsoft-365-network-connectivity-principles?view=o365-worldwide#BKMK_Categories

    "o365_categories":{                  
        "all": True|False              -> Create a single date set containing all URLs (all categories)
        "optimize: True|False          -> Create a data set containing O365 "Optimize" category URLs (note that the optimized URLs are in Exchange and "SharePoint service areas)
        "default": True|False          -> Create a data set containing O365 "Allow" category URLs
        "allow": True|False            -> Create a data set containing O365 "Default" category URLs
    }

<br />
  
**Required O365 endpoints to import** - O365 required endpoints or all endpoints. Importing all endpoints includes non-O365 URLs that one may not want to bypass (ex. www.youtube.com). It is recommended to leave this enabled/true (only download required URLs).

    "only_required": True|False        -> false=import all URLs, true=Office 365 required only URLs

<br />
  
**Excluded URLs** - (URL pattern matching is supported). Provide URLs in list format - ex. ["m.facebook.com", ".itunes.apple.com", "bit.ly"]. Even with "only_required" enabled, some non-Microsoft URLs are still included, mostly Certificate Authorities. The default settings include the set of CA URLs to exclude, but additional URLs can be added to this list as required. The list supports "ends-with" pattern matching.

    "excluded_urls": []

<br />
  
**Included URLs (ALL)** - Includes a set of URLs in the **ALL** category. The URL can either be an exact match (ex. www.example.com), or start with a wildcard (ex. \*.example.com).     

    "included_urls_all": [
      "www.foo.com",
      "www.bar.com",
      "*.test.com"
    ] 

<br /> 
  
**Included URLs (OPTIMIZE)** - Includes a set of URLs in the **OPTIMIZE** category. The URL can either be an exact match (ex. www.example.com), or start with a wildcard (ex. \*.example.com).     

    "included_urls_optimize": [
      "www.foo.com",
      "www.bar.com",
      "*.test.com"
    ] 

<br />
  
**Included URLs (DEFAULT)** - Includes a set of URLs in the **DEFAULT** category. The URL can either be an exact match (ex. www.example.com), or start with a wildcard (ex. \*.example.com).*     

    "included_urls_default": [
      "www.foo.com",
      "www.bar.com",
      "*.test.com"
    ] 

<br />
  
**Included URLs (ALLOW)** - Includes a set of URLs in the **ALLOW** category. The URL can either be an exact match (ex. www.example.com), or start with a wildcard (ex. \*.example.com).     

    "included_urls_allow": [
      "www.foo.com",
      "www.bar.com",
      "*.test.com"
    ] 

<br />
  
**Excluded IPs** - (IP must be exact match to IP as it exists in JSON record - IP/CIDR mask cannot be modified). Provide IPs in list format - ex. ["191.234.140.0/22", "2620:1ec:a92::152/128"].

    "excluded_ips": [] 

<br />
  
**System-level configuration settings**

    "system":{
        "log_level": 1                       -> 0 = no logging, 1 = normal logging, 2 = verbose logging
        "ca_bundle": "ca-bundle.crt"         -> The CA certificate bundle to use for validating the remote server certificate
        "working_directory": "/shared/o365"  -> The working directory to install and run the script from
        "retry_attempts": 3                  -> Number of attempts to make if initial remote call fails
        "retry_delay": 300                   -> Delay between attempts
    }
   
**System-level configuration settings**

    "schedule":{
        "periods":"none"                     -> The period, "monthly", "weekly", "daily", or "none" to run the script
        "run_date":1                         -> The day of the week for weekly (0-6 Sunday-Saturday), or day of the month for monthly (1-31) to run the script
        "run_time":"04:00"                   -> The 24-hour time to run the script (ex. "04:00") - required for daily/weekly/monthly
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
    "included_urls_all": [],
    "included_urls_optimize": [],
    "included_urls_default": [],
    "included_urls_allow": [],
    "excluded_ips": [],
    "system": {
        "log_level": 1,
        "ca_bundle": "ca-bundle.crt",
        "working_directory": "/tmp/o365",
        "retry_attempts":3,
        "retry_delay":300
    },
    "schedule":{
        "periods":"none",
        "run_date":1,
        "run_time":"04:00",
        "start_date":"",
        "start_time":""
    }
}
```

---

**Improvements**
- Update to enable hash-based change detection
- Update to enable URL category search feature
- Update to enable separate allow, optimize, default, and all URL include blocks
- Update to make the script compatible with python2 and python3 with platform check
