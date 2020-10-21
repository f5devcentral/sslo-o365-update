# F5 SSL Orchestrator Office 365 URL Update Script
A small Python utility to download and maintain the dynamic set of Office 365 URLs as data groups and custom URL categories on the F5 BIG-IP, for use with SSL Orchestrator.

[![Releases](https://img.shields.io/github/v/release/f5devcentral/sslo-o365-update.svg)](https://github.com/f5devcentral/sslo-o365-update/releases)

### Version support
This utility works on BIG-IP 14.1 and above, SSL Orchestrator 5.x and above.

### How to install 
- Download the script onto the F5 BIG-IP:

  `curl -k https://raw.githubusercontent.com/f5devcentral/sslo_o365_update/main/sslo_o365_update.py -o sslo_o365_update.py`

- Run the script with the *--install* option and a time interval. The time interval controls periodic updates, in seconds. Microsoft publishes the endpoint data at the beginning of each month, so any time interval between 3600 (1 hour) and 604800 (1 week) is optimal. The endpoint version number is tracked internally, so a full URL download will only happen if this value changes. Otherwise the periodic script call will simply check and compare the latest version number.

  `python sslo_o365_update.py --install 3600`

### How to modify the configuration
- Edit the configuration json file via interactive tmsh. Use standard VIM commands for editing.

  `tmsh`
  
  `edit sys file ifile o365_config.json`

### How to uninstall
- Run the script with the *--uninstall* option. This will remove the iCall script, iCall periodic handler, and configuration json file. The URL categories, data groups, and working directory will remain.

  `python sslo_o365_update.py --uninstall`

### How to force an update
- With the configuration setting "force_refresh" set to False, a URL update will only occur if the endpoint version has changed. The --force option overrides to force a refresh.

  `python sslo_o365_update.py --force`

### HA installation
- Perform the install operations on both units in an HA environment and then sync. The script runs independently on each peer and will not trigger an out-of-sync indication when updates are made.

---

### The configuration environment
The installed script creates a working directory (/shared/o365), a configuration (iFile) json file, an iCall script, and iCall script periodic handler. The configuration json file controls the various settings of the script.


***Endpoint** - Microsoft Web Service Customer endpoints (ENABLE ONLY ONE ENDPOINT). These are the set of URLs defined by customer endpoints as described here: https://docs.microsoft.com/en-us/office365/enterprise/urls-and-ip-address-ranges. Valid values are **"Worldwide"**, **"USGovDoD"**, **"USGovGCCHigh"**, **"China"**, **"Germany"**.*

    endpoint": "Worldwide"


***O365 "Service Areas"** - O365 endpoints to consume, as described here: https://docs.microsoft.com/en-us/office365/enterprise/urls-and-ip-address-ranges. The "common" service area should remain enabled as it contains the bulk of the URLs.*

    service_areas
        common: true|false                -> Microsoft 365 Common and Office Online"
        exchange: true|false              -> Exchange Online  
        sharepoint: true|false            -> SharePoint Online and OneDrive for Business
        skype: true|false                 -> Skype for Business Online and Microsoft Teams


***Outputs** - O365 Record objects to create*    

    outputs
        url_categories: true|false        -> Create URL categories
        url_datagroups: true|false        -> Create URL data groups
        ip4_datagroups: true|false        -> Create IPv4 data groups
        ip6_datagroups: true|false        -> Create IPv6 data groups


***O365 Categories** - create a single URL data set, and/or separate data sets for O365 Optimize/Default/Allow categories. The categories and recommended actions for each is described here: https://docs.microsoft.com/en-us/microsoft-365/enterprise/microsoft-365-network-connectivity-principles?view=o365-worldwide#BKMK_Categories*

    o365_categories                  
        all: true|false                   -> Create a single date set containing all URLs (all categories)
        optimize: true|false              -> Create a data set containing O365 "Optimize" category URLs (note that the optimized URLs are in Exchange and SharePoint service areas)
        default: true|false               -> Create a data set containing O365 "Allow" category URLs
        allow: true|false                 -> Create a data set containing O365 "Default" category URLs


***Required O365 endpoints to import** - O365 required endpoints or all endpoints. Importing all endpoints includes non-O365 URLs that one may not want to bypass (ex. www.youtube.com). It is recommended to leave this enabled/true (only download required URLs).*

    only_required: true|false             -> false=import all URLs, true=Office 365 required only URLs


***Excluded URLs** - (URL pattern matching is supported). Provide URLs in list format - ex. ["m.facebook.com", ".itunes.apple.com", "bit.ly"]. Even with "only_required" enabled, some non-Microsoft URLs are still included, mostly Certificate Authorities. The default settings include the set of CA URLs to exclude, but additional URLs can be added to this list as required. The list supports "ends-with" pattern matching.*

    excluded_urls: []


***Included URLs** - (URL must be exact match to URL as it exists in JSON record - pattern matching not supported). Provide URLs in list format - ex. ["foo.com", "bar.com"].*     

    included_urls: [] 
   
   
***Excluded IPs** - (IP must be exact match to IP as it exists in JSON record - IP/CIDR mask cannot be modified). Provide IPs in list format - ex. ["191.234.140.0/22", "2620:1ec:a92::152/128"].*

    excluded_ips: [] 

***System-level configuration settings***

    system:
        force_refresh: true|false        -> Enable this to force the script to ignore the local endpoint version tracking and to alway download
        log_level: 1                     -> 0 = no logging, 1 = normal logging, 2 = verbose logging
        ha_config: 0                     -> 0 = stand alone, 1 = HA paired
        device_group: "device-group-1".  -> Name of Sync-Failover Device Group.  Required if "ha_config" is true (1).
   
 
---

**Extra**

In this environment it is also possible to manage the configuration remotely by updating the json iFile content.

- Obtain a copy of the existing json configuration data using the interactive tmsh edit (see above "How to modify the configuration") and save to a local file. Edit as required. 

- Determine the file size in bytes (after editing). On some systems, the following works: **du -b config.json**. On a Mac, you can use the following: **ls -l config.json |awk -F" " '{print $5 }'**.

- Upload the file to a staging path. Modify the "Content-Range" header value to indicate the start-end range (0 - size-1)/size.

  `curl -isk -u admin:admin -H "Content-Type: application/octet-stream" -H "Content-Range: 0-1066/1067" --data-binary "@config.json" https://big-ip/mgmt/shared/file-transfer/uploads/config.json`

- Optional, combine the size calculation and upload into a single call:

  ``size=`ls -l config.json |awk -F" " '{print $5 }'` && curl -isk -u admin:admin -H "Content-Type: application/octet-stream" -H "Content-Range: 0-$(expr ${size} - 1)/${size}" --data-binary "@config.json" https://big-ip/mgmt/shared/file-transfer/uploads/config.json``

- Update the iFile object:

  `curl -vk -u admin:admin -X PUT -H "Content-Type: application/json" -d '{"name": "o365_config.json", "source-path": "file:/var/config/rest/downloads/config.json"}' https://big-ip/mgmt/tm/sys/file/ifile/o365_config.json`


