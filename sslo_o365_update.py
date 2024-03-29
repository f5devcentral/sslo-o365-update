#!/bin/python
# -*- coding: utf-8 -*-
# O365 URL/IP update automation for BIG-IP

version = "7.3.0"

# Last Modified: June 2022
# Update author: Kevin Stewart, Sr. SSA F5 Networks
# Contributors: SSLO product engineering
# Contributors: Regan Anderson, Brett Smith, F5 Networks
# Original author: Makoto Omura, F5 Networks Japan G.K.
#
# >>> NOTE: THIS VERSION OF THE OFFICE 365 SCRIPT IS SUPPORTED BY SSL ORCHESTRATOR 5.0 OR HIGHER <<<
#
# Updated for SSL Orchestrator by Kevin Stewart, SSA, F5 Networks
# Update 20220613 - to enable hash-based change detection
# Update 20220504 - to enable URL category search feature
# Update 20220412 - to enable separate allow, optimize, default, and all URL include blocks
# Update 20220106 - to make the script compatible with python2 and python3 with platform check
# Update 20211231 - to make the script compatible with python3
# Update 20211119 - to update messages based on doc team review
# Update 20211103 - to support logging to /var/log/apm
#   - Updated to only retry if --force isn't passed, since the UI request would timeout
#   - Updated names of URL categories to match the names created by BIGIQ
# Update 20211012 - to support additional enhancements
#   - Updated to correct HA sync flag issue on URL update (no longer triggers out-of-sync)
#   - Updated to support retry_attempts and retry_delay options
# Update 20210927 - to support additional enhancements
#   - Updated to support more correct sys.exit(1) and stderr output for errors
# Update 20210910 - to support additional enhancements (by Kevin Stewart)
#   - Updated to support TMSH and crontab execution by non-root user
#   - Updated log file to location under working directory
# Update 20210823 - to support additional enhancements (by Kevin Stewart)
#   - Updated to address ip4/ip6 datagroup issue
#   - Updated to collapse IPv4 and IPv6 datagroup configuration into a single option (on/off)
#   - Updated to add 'none' option to schedule (no schedule)
#   - Updated to add 'daily' option to schedule
#   - Updated to add CA bundle selection for server certificate validation
#   - Updated to address url_included issue (was not adding urls)
#   - Updated to add last_run information fields in the configuration JSON
#   - Updated to add validation of O365 URL data response (in case of good response with no/bad data)
#   - Updated to add STDOUT messages for successful install, uninstall, force-update, and all errors
#   - Updated to add [tag] for verbose messaging
# Update 20210601 - to support additional enhancements (by Kevin Stewart)
#   - Updated to class-based Python script
#   - Updated to support --config (serialized JSON string input) and --configfile (JSON file) install options
#   - Updated to support --full_uninstall option to delete all configurations (local files, URL categories, datagroups)
#   - Updated to support --printconfig option to show the running configuration (JSON)
#   - Updated to support using system proxy settings (System : Configuration : Device : Upstream Proxy)
#   - Updated to support /etc/cron.d/0hourly scheduler (replaces iCall periodic) for more granular m/d/Y HH:mm scheduling
#   - Updated to support more comprehensive config input validation
# Update 20210119 - added support for explicit proxy gateway if required for Internet access (by Kevin Stewart)
# Update 20201104 - resolved URL category format issue (by Kevin Stewart)
# Update 20201008 - to support additional enhancements (by Kevin Stewart)
#   - Updated to support HA isolation mode (both peers perform updates and do not an trigger out-of-sync)
#   - Updated to resolve issue if multiple versions of configuration iFile exists (takes latest)
#   - Updated to include --force option to force a manual update (irrespective of config force_o365_record_refresh value)
# Update 20200925 - to support additional enhancements (by Kevin Stewart)
#   - Updated to support O365 optimize/allow/default categories as separate outputs
#   - Updated to support options to output to URL categories and/or URL data groups
#   - Updated to support included URLs
#   - Updated to support configuration stored in iFile
#   - Updated to include install|uninstall functions
# Update 20200207 - to support additional enhancements (by Kevin Stewart)
#   - Updated VERSION check routine to extract desired customer endpoint URI (previously was static "Worldwide")
#   - Updated to remove excluded_urls and excluded_ips
# Update 20200130 - to support the following new functionality (by Regan Anderson)
#   - Changed default working directory to /shared/o365/
#   - Removed deprecated Yammer service area
#   - Added ability to import only "Required" records (and set as default)
#   - Added URL and IP exclusion lists to manually exclude entries from being imported
#   - Adjusted URL category records to support HTTP schemes in SSLOv7 (http:// and https://)
#   - Added external data group support for URLs
#   - Added external data group import function for IPv4/IPv6
#
# To install:
#   - Download the script onto the F5 BIG-IP:
#     curl -k https://raw.githubusercontent.com/kevingstewart/sslo_o365_update/main/sslo_o365_update.py -o sslo_o365_update.py
#
#   - Run the script with the --install option
#     python sslo_o365_update.py --install
#
#   - Optionally add a custom configuration (JSON) via the following options (with --install). See json_config_data variable below for defaults.
#     - Load the default configuration                      -> python sslo_o365_update.py --install
#     - Load configuration from serialized JSON string      -> python sslo_o365_update.py --install --config <${JSON_STRING}>
#     - Load configuration from JSON file                   -> python sslo_o365_update.py --install --configfile <config.json>
#
# To modify the configuration.
#     - Initiate the --install process again with a new --config or --configfile argument
#
# To uninstall:
#   - Two options:
#     - Run the script with the --uninstall option. This will remove the running configuration.
#     - Run the script with the --full_uninstall option. This will remove the running configuration, URL categories, and datagroups.
#
# The installed script creates a working directory (default: "/shared/o365"), a configuration (iFile) json file, and scheduler.
#
# The configuration json file controls the various settings of the script. See json_config_data variable below for defaults.
#
#     Microsoft Web Service Customer endpoints (ENABLE ONLY ONE ENDPOINT)
#     These are the set of URLs defined by customer endpoints as described here: https://docs.microsoft.com/en-us/office365/enterprise/urls-and-ip-address-ranges
#     Valid values are [Worldwide, USGovDoD, USGovGCCHigh, China, Germany]
#     "endpoint": "Worldwide"
#
#     O365 "SeviceArea" (O365 endpoints) to consume, as described here: https://docs.microsoft.com/en-us/office365/enterprise/urls-and-ip-address-ranges
#     "service_areas":
#         "common": true|false            -> Microsoft 365 Common and Office Online"
#         "exchange": true|false          -> Exchange Online
#         "sharepoint": true|false        -> SharePoint Online and OneDrive for Business
#         "skype": true|false             -> Skype for Business Online and Microsoft Teams
#
#     O365 Record objects to create
#     "outputs":
#         "url_categories": true|false    -> Create URL categories
#         "url_datagroups": true|false    -> Create URL data groups
#         "ip_datagroups": true|false     -> Create IP data groups
#
#     O365 Category creation, create a single URL data set, and/or separate data sets for O365 Optimize/Default/Allow categories
#     "o365_categories":
#         "all": true|false               -> Create a single date set containing all URLs (all categories)
#         "optimize": true|false          -> Create a data set containing O365 Optimize category URLs (note that the optimized URLs are in Exchange and SharePoint service areas)
#         "default": true|false           -> Create a data set containing O365 Allow category URLs
#         "allow": true|false             -> Create a data set containing O365 Default category URLs
#
#     O365 Endpoints to import - O365 required endpoints or all endpoints
#     WARNING: "import all" includes non-O365 URLs that one may not want to bypass (ex. www.youtube.com)
#     "only_required": true|false         -> false=import all URLs, true=Office 365 required only URLs
#
#     Excluded URLs (URL pattern matching is supported)
#     Provide URLs in list format - ex. ["m.facebook.com", ".itunes.apple.com", "bit.ly"]
#     "excluded_urls": []
#
#     Included URLs (URL must be exact match to URL as it exists in JSON record - pattern matching not supported)
#     Provide URLs in list format for each O365 category- ex. ["m.facebook.com", ".itunes.apple.com", "bit.ly"]
#     "included_urls": {
#        "all" :  [],
#        "optimized" : [],
#        "default" : [],
#        "allow" : []
#       }
#
#     Excluded IPs (IP must be exact match to IP as it exists in JSON record - IP/CIDR mask cannot be modified)
#     Provide IPs in list format - ex. ["191.234.140.0/22", "2620:1ec:a92::152/128"]
#     "excluded_ips": []
#
#     "system":
#         "log_level": 1                        -> 0=none, 1=normal, 2=verbose
#         "ca_bundle": "ca-bundle.crt"          -> CA certificate bundle to use for validating the remote server certificate
#         "working_directory":"/shared/o365"    -> Working directory for running configuration files
#         "retry_attempts":3                    -> Number of times to try a network operation (URL update). Setting to 0 disables retry. Default is 3 attempts
#         "retry_delay":300                     -> Number of seconds to wait between retries. Default is 300 seconds (5 minutes)
#
#     "schedule":
#         "periods":"monthly|weekly|daily|none" -> When to trigger updates ('monthly', 'weekly', 'daily', or 'none') -- default(none)
#         "run_date":0                          -> Day of week or day of month to run the script, as controlled by /etc/cron.d/0hourly -- default(0 Sunday)
#         "run_time":"04:00"                    -> 24-hour time to run the script, as controlled by /etc/cron.d/0hourly -- default("04:00")
#         "start_date":""                       -> Standard "m/d/Y" date format to control when script is allowed to run
#         "start_time":""                       -> Standard 24-hour "HH:mm" time format to control when script is allowed to run
#
#
# This Sample Software provided by the author is for illustrative
# purposes only which provides customers with programming information
# regarding the products. This software is supplied "AS IS" without any
# warranties and support.
#
# The author(s) assume no responsibility or liability for the use of the
# software, conveys no license or title under any patent, copyright, or
# mask work right to the product.
#
# The author(s) reserve the right to make changes in the software without
# notification. The author also make no representation or warranty that
# such application will be suitable for the specified use without
# further testing or modification.
#-----------------------------------------------------------------------

import platform, fnmatch, uuid, os, pwd, re, json, time, datetime, sys, argparse, copy, ssl, hashlib

if platform.python_version().startswith("2."):
    import commands as shell
    import urllib2 as urlrequest
elif platform.python_version().startswith("3."):
    import subprocess as shell
    from urllib import request as urlrequest

#-----------------------------------------------------------------------
# Default JSON configuration
#-----------------------------------------------------------------------
json_config_data = {
    "endpoint": "Worldwide",
    "service_areas": {
        "common": True,
        "exchange": True,
        "sharepoint": True,
        "skype": True
    },
    "outputs": {
        "url_categories": True,
        "url_datagroups": False,
        "ip_datagroups": True
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
        ".verisign.com",
        ".globalsign.net",
        ".globalsign.com",
        ".geotrust.com",
        ".omniroot.com",
        ".letsencrypt.org",
        ".public-trust.com",
        "platform.linkedin.com"
    ],
    "included_urls": {
        "all": [],
        "optimized": [],
        "default": [],
        "allow": []
    },
    "excluded_ips": [],
    "system": {
        "log_level": 1,
        "ca_bundle": "ca-bundle.crt",
        "working_directory": "/shared/o365",
        "retry_attempts":3,
        "retry_delay":300
    },
    "schedule":{
        "periods":"none",
        "run_date":1,
        "run_time":"04:00",
        "start_date":"",
        "start_time":""
    },
    "help": "If the Office365 configuration is deleted from the command line using the full_uninstall feature of the Python script and created again, the URL Category IDs will change. Therefore, if the SSL Orchestrator security policy uses any of these categories, the policy will need to be redeployed.",
    "status":{
        "description":"",
        "last_run":"",
        "next_run":"",
        "last_hash_includedUrls" : {},
        "last_hash_excludedUrls" : "",
        "last_hash_excludedIPs" : ""
    }
}

##-----------------------------------------------------------------------
## System Options - Modify only when necessary
##-----------------------------------------------------------------------
## O365 custom URL category names
o365_category = "Office_365_All\(Managed\)"
o365_category_optimized = "Office_365_Optimized\(Managed\)"
o365_category_default = "Office_365_Default\(Managed\)"
o365_category_allow = "Office_365_Allow\(Managed\)"

## O365 data group names
dg_name_urls = "O365_URLs"
dg_name_ipv4 = "O365_IPv4"
dg_name_ipv6 = "O365_IPv6"
o365_dg = "Office_365_Managed_All"
o365_dg_optimize = "Office_365_Managed_Optimized"
o365_dg_default = "Office_365_Managed_Default"
o365_dg_allow = "Office_365_Managed_Allow"
o365_dg_ipv4 = "Office_365_Managed_IPv4"
o365_dg_ipv6 = "Office_365_Managed_IPv6"

## Microsoft Web Service URLs
url_ms_o365_endpoints = "endpoints.office.com"
url_ms_o365_version = "endpoints.office.com"
uri_ms_o365_version = "/version?ClientRequestId="


class o365UrlManagement:

    ## Init function (set local variables)
    def __init__(self):
        self.customer_endpoint = ""
        self.service_areas_common = ""
        self.service_areas_exchange = ""
        self.service_areas_sharepoint = ""
        self.service_areas_skype = ""
        self.output_url_categories = ""
        self.output_url_datagroups = ""
        self.output_ip_datagroups = ""
        self.o365_categories_all = ""
        self.o365_categories_optimize = ""
        self.o365_categories_default = ""
        self.o365_categories_allow = ""
        self.only_required = ""
        self.excluded_urls = ""
        self.included_urls_allow = ""
        self.included_urls_optimized = ""
        self.included_urls_default = ""
        self.included_urls_all = ""
        self.excluded_ips = ""
        self.log_level = ""
        self.ca_bundle = ""
        self.work_directory = ""
        self.json_config = ""
        self.json_config_file = ""
        self.force_update = False
        self.config_data = ""
        self.logdir = ""
        self.retry_attempts = 0
        self.retry_delay = 0


    ##-----------------------------------------------------------------------
    ## Logging function
    ##  Purpose: sends a message to the log file
    ##  Parameters:
    ##      lev         = level of this meesage
    ##      log_lev     = system configured log level (for comparison)
    ##      log_dir     = location of log file
    ##      msg         = log message
    ##  Example:
    ##      self.log(2, self.log_level, self.logdir, "Application service not found. Creating o365_update.app/o365_update")
    ##-----------------------------------------------------------------------
    def log(self, lev, log_lev, log_dir, msg):
        ## Create the log directory if it's doesn't exist
        if not os.path.isdir(log_dir):
                os.mkdir(log_dir)

        ## Create the log file if it doesn't exist
        if not os.path.exists(log_dir + "/o365_update"):
            f = open(log_dir + "/o365_update", "w")
            f.write("\n")
            f.flush()
            f.close()

        if int(log_lev) >= int(lev):
            log_string = "{0:%Y-%m-%d %H:%M:%S}".format(datetime.datetime.now()) + " " + msg + "\n"
            f = open(log_dir + "/o365_update", "a")
            f.write(log_string)
            f.flush()
            f.close()
        return

    ##-----------------------------------------------------------------------
    ## Event logging function
    ##  Purpose: sends a message using /usr/bin/logger to /var/log/apm for tracking events
    ##  Parameters:
    ##      lev         = level of this meesage
    ##      msg         = log message
    ##  Example:
    ##      self.event_log(2, "VERSION request to MS web service was successful.")
    ##-----------------------------------------------------------------------
    def event_log(self, lev, msg):
        ## For event logs 1 -> error, 2 -> notice
        level = "error" if lev == 1 else "notice"

        ## local1 logs to /var/log/apm, and the SSLO product subset is C4.
        ## Use 1000 for log msg id to not collide with log messages on BIGIP
        log_cmd = "/usr/bin/logger -p local1." + level + " \"01c41000: " + msg + "\""
        result = shell.getoutput(log_cmd)


    ##-----------------------------------------------------------------------
    ## Show help function
    ##  Purpose: shows the help syntax
    ##  Parameters: none
    ##-----------------------------------------------------------------------
    def show_help(self):
        print("Office 365 URL Management Script. Version: " + version)
        print("\nCommand line options for this application are:\n")
        print("--help                       -> Show this help message and exit.")
        print("--install                    -> Install the script.")
        print("--uninstall                  -> Uninstall the script.")
        print("--full_uninstall             -> Uninstall the script. Remove everything.")
        print("--force                      -> Force an update.\n")
        print("--config CONFIG              -> Used with --install. Provide alternate JSON configuration information from a serialized JSON string object.")
        print("--config_file CONFIG_FILE    -> Used with --install. Provide alternate JSON configuration information from a JSON file.\n")
        print("--printconfig                -> Show the running configuration.\n")
        print("--search                     -> Search the Office365 URL categories.\n")

        print("Examples:")
        print("Install with default configuration           ->  python " + os.path.basename(__file__) + " --install")
        print("Install with serialized JSON configuration   ->  python " + os.path.basename(__file__) + " --install --config ${json_string}")
        print("Install with JSON file:                      ->  python " + os.path.basename(__file__) + " --install --configfile file.json")
        print("Install and force immediate URL update       ->  python " + os.path.basename(__file__) + " --install --force")
        print("Force an update                              ->  python " + os.path.basename(__file__) + " --force")
        print("Uninstall but keep categories/datagroups     ->  python " + os.path.basename(__file__) + " --uninstall")
        print("Uninstall and remove categories/datagroups   ->  python " + os.path.basename(__file__) + " --full_uninstall")
        print("Search for a URL in the Office365 categories ->  python " + os.path.basename(__file__) + " --search https://smtp.office365.com\n\n")
        sys.exit(0)


    ##-----------------------------------------------------------------------
    ## Get config function
    ##  Purpose: reads the JSON/iFile configuration into (self) local variables
    ##  Parameters: none
    ##-----------------------------------------------------------------------
    def get_config(self):
        try:
            ## Find all versions of the configuration iFile
            o365_config = ""
            entry_array = []
            fileList = os.listdir('/config/filestore/files_d/Common_d/ifile_d/')
            pattern = "*o365_config.json*"
            for entry in fileList:
                if fnmatch.fnmatch(entry, pattern):
                    entry_array.append("/config/filestore/files_d/Common_d/ifile_d/" + entry)

            ## Find the latest version of the configuration iFile
            if entry_array:
                o365_config = max(entry_array, key=os.path.getctime)

            if o365_config == "":
                sys.stderr.write("\nIt appears that O365 URL Updater configuration has not been saved yet. Aborting (1000).\n\n[help-info] To install this script, issue the command \"" + os.path.basename(__file__) + " --install\"\n")
                self.show_help()

            try:
                f = open(o365_config, "r")
                f_content = f.read()
                f.close()
                self.config_data = json.loads(f_content)

                ## Read configuration parameters from the json config
                self.customer_endpoint           = self.config_data["endpoint"]
                self.service_area_common         = self.config_data["service_areas"]["common"]
                self.service_area_exchange       = self.config_data["service_areas"]["exchange"]
                self.service_area_sharepoint     = self.config_data["service_areas"]["sharepoint"]
                self.service_area_skype          = self.config_data["service_areas"]["skype"]
                self.output_url_categories       = self.config_data["outputs"]["url_categories"]
                self.output_url_datagroups       = self.config_data["outputs"]["url_datagroups"]
                self.output_ip_datagroups        = self.config_data["outputs"]["ip_datagroups"]
                self.o365_categories_all         = self.config_data["o365_categories"]["all"]
                self.o365_categories_optimize    = self.config_data["o365_categories"]["optimize"]
                self.o365_categories_default     = self.config_data["o365_categories"]["default"]
                self.o365_categories_allow       = self.config_data["o365_categories"]["allow"]
                self.only_required               = self.config_data["only_required"]
                self.excluded_urls               = self.config_data["excluded_urls"]
                self.included_urls_allow         = self.config_data["included_urls"]["allow"]
                self.included_urls_optimized     = self.config_data["included_urls"]["optimized"]
                self.included_urls_default       = self.config_data["included_urls"]["default"]
                self.included_urls_all           = self.config_data["included_urls"]["all"]
                self.excluded_ips                = self.config_data["excluded_ips"]
                self.log_level                   = self.config_data["system"]["log_level"]
                self.ca_bundle                   = self.config_data["system"]["ca_bundle"]
                self.work_directory              = self.config_data["system"]["working_directory"]
                self.logdir                      = self.config_data["system"]["working_directory"] + "/log"
                self.retry_attempts              = self.config_data["system"]["retry_attempts"]
                self.retry_delay                 = self.config_data["system"]["retry_delay"]
                self.schedule_periods            = self.config_data["schedule"]["periods"]
                self.schedule_run_date           = self.config_data["schedule"]["run_date"]
                self.schedule_run_time           = self.config_data["schedule"]["run_time"]
                self.schedule_start_date         = self.config_data["schedule"]["start_date"]
                self.schedule_start_time         = self.config_data["schedule"]["start_time"]
                self.status                      = self.config_data["status"]

            except:
                sys.stderr.write("\nERROR: It appears the JSON configuration file is either missing or corrupt. Aborting (1001).\n[help-info] Run the script again with the --install option to repair\n.")
                self.show_help()

        except:
            sys.stderr.write("\nERROR: It appears that O365 URL Updater configuration has not been saved yet. Aborting (1002).\n\n[help-info] To install this script, issue the command \"" + os.path.basename(__file__) + " --install\"\n")
            self.show_help()


    ##-----------------------------------------------------------------------
    ## Show running configuration function
    ##  Purpose: prints the running configuration to stdout
    ##  Parmeters: none
    ##-----------------------------------------------------------------------
    def print_config(self):
        self.get_config()
        this_json = json.dumps(self.config_data, indent = 4)
        print(this_json)
        sys.exit(1)

    
    ##-----------------------------------------------------------------------
    ## Search function
    ##  Purpose: search for a URL in the Office365 categories
    ##  Parmeters: URL (ex. https://smtp.office365.com)
    ##-----------------------------------------------------------------------
    def search(self, url):
        CAT_ALL = "o365_update.app/Office_365_All(Managed)"
        CAT_ALLOW = "o365_update.app/Office_365_Allow(Managed)" 
        CAT_OPT = "o365_update.app/Office_365_Optimized(Managed)"
        CAT_DEF = "o365_update.app/Office_365_Default(Managed)"

        if not ((url.startswith("https://")) or (url.startswith("http://"))):
            print("\nURL argument format must include protocol")
            print("Example: python o365_lookup.py https://smtp.office365.com\n")
            sys.exit(0)

        found_list = []

        ## ALL Search
        result = shell.getoutput("tmsh -a list sys url-db url-category \"" + CAT_ALL + "\" urls | grep -E '\s+http.*' | sed -e 's/ //g;s/{//g;s/\\\//g'")
        for x in result.splitlines():
            pattern = x.rstrip("/")
            match = fnmatch.fnmatch(url, pattern)
            if (match):
                found_list.append("Office_365_All(Managed):\t" + pattern)

        ## ALLOW Search
        result = shell.getoutput("tmsh -a list sys url-db url-category \"" + CAT_ALLOW + "\" urls | grep -E '\s+http.*' | sed -e 's/ //g;s/{//g;s/\\\//g'")
        for x in result.splitlines():
            pattern = x.rstrip("/")
            match = fnmatch.fnmatch(url, pattern)
            if (match):
                found_list.append("Office_365_Allow(Managed):\t" + pattern)

        ## OPT Search
        result = shell.getoutput("tmsh -a list sys url-db url-category \"" + CAT_OPT + "\" urls | grep -E '\s+http.*' | sed -e 's/ //g;s/{//g;s/\\\//g'")
        for x in result.splitlines():
            pattern = x.rstrip("/")
            match = fnmatch.fnmatch(url, pattern)
            if (match):
                found_list.append("Office_365_Optimized(Managed):\t" + pattern)

        ## DEF Search
        result = shell.getoutput("tmsh -a list sys url-db url-category \"" + CAT_DEF + "\" urls | grep -E '\s+http.*' | sed -e 's/ //g;s/{//g;s/\\\//g'")
        for x in result.splitlines():
            pattern = x.rstrip("/")
            match = fnmatch.fnmatch(url, pattern)
            if (match):
                found_list.append("Office_365_Default(Managed):\t" + pattern)
        
        if (len(found_list) > 0):
            print("\nThe following URL matches were discovered:\n") 
            for found_url in found_list:
                print(found_url)
                
            print("\n\n")

        else:
            print("\nNo URL matches were found\n")

        sys.exit(1)


    ##-----------------------------------------------------------------------
    ## URL parser function
    ##  Purpose: clean up an return URLs submitted in JSON config
    ##      - no http://
    ##      - no https://
    ##      - no trailing /
    ##      - no wildcards (*)
    ##      - remove resulting duplicates
    ##  Prameters: URL list
    ##-----------------------------------------------------------------------
    def url_parser(self, urllist):
        urlscleaned = []
        for url in urllist:
            ## convert all to lowercase
            this_url = url.lower()

            ## test for http://www.foo.com => convert to www.foo.com
            if this_url.startswith("http://"):
                this_url = this_url.replace("http://","")

            ## test for https://www.foo.com => convert to www.foo.com
            if this_url.startswith("https://"):
                this_url = this_url.replace("https://","")

            ## test for and remove trailing /
            if this_url.endswith("/"):
                this_url = this_url[:-1]

            ## remove any wildcards (*)
            this_url = this_url.replace("*","")

            urlscleaned.append(this_url)

        ## de-duplicate and return the remaining list
        urlsdeduped = list(set(urlscleaned))
        return urlsdeduped


    ##-----------------------------------------------------------------------
    ## Hash function
    ##  Purpose: get the hash of a supplied parameter and return the hash value
    ##  Parameters:
    ##      jsonstr     = supplied JSON configuration
    ##-----------------------------------------------------------------------
    def get_hashedValue(self, input):
        input.sort()
        return hashlib.md5(str(input).encode('utf-8')).hexdigest()

    ##-----------------------------------------------------------------------
    ## JSON update function
    ##  Purpose: update imported json data to include required attributes and/or defaults if keys are omitted
    ##  Parameters:
    ##      jsonstr     = supplied JSON configuration
    ##-----------------------------------------------------------------------
    def update_json(self, jsonstr):
        json_data = copy.deepcopy(json_config_data)

        ##status
        if "status" in jsonstr:
            if "description" in jsonstr["status"]:
                json_data["status"]["description"] = jsonstr["status"]["description"]
            else:
                json_data["status"]["description"] = ""

            if "last_run" in jsonstr["status"]:
                json_data["status"]["last_run"] = jsonstr["status"]["last_run"]
            else:
                json_data["status"]["last_run"] = ""

            if "next_run" in jsonstr["status"]:
                json_data["status"]["next_run"] = jsonstr["status"]["next_run"]
            else:
                json_data["status"]["next_run"] = ""

            if "last_hash_includedUrls" in jsonstr["status"]:
                json_data["status"]["last_hash_includedUrls"] = jsonstr["status"]["last_hash_includedUrls"]
            else:
                json_data["status"]["last_hash_includedUrls"] = {}

            if "last_hash_excludedUrls" in jsonstr["status"]:
                json_data["status"]["last_hash_excludedUrls"] = jsonstr["status"]["last_hash_excludedUrls"]
            else:
                json_data["status"]["last_hash_excludedUrls"] = ""

            if "last_hash_excludedIPs" in jsonstr["status"]:
                json_data["status"]["last_hash_excludedIPs"] = jsonstr["status"]["last_hash_excludedIPs"]
            else:
                json_data["status"]["last_hash_excludedIPs"] = ""

        ## endpoint
        if "endpoint" in jsonstr:
            json_data["endpoint"] = jsonstr["endpoint"]

            ## Input validation: ensure value is one of: Worldwide, USGovDoD, USGovGCCHigh, China, or Germany
            if json_data["endpoint"] not in {"Worldwide", "USGovDoD", "USGovGCCHigh", "China", "Germany"}:
                raise Exception('Endpoint value must be one of: \"Worldwide\", \"USGovDoD\", \"USGovGCCHigh\", \"China\", or \"Germany\". [1014]')
                sys.exit(1)

        ## service_areas
        if "service_areas" in jsonstr:

            ## service_areas:common
            if "common" in jsonstr["service_areas"]:
                json_data["service_areas"]["common"] = jsonstr["service_areas"]["common"]

                ## Input validation: ensure value is boolean
                if type(json_data["service_areas"]["common"]) != bool:
                    raise Exception('Service Areas "common" value must be a Boolean True or False. [1021]')
                    sys.exit(1)
            else:
                ## Default True
                json_data["service_areas"]["common"] = True

            ## service_areas:exchange
            if "exchange" in jsonstr["service_areas"]:
                json_data["service_areas"]["exchange"] = jsonstr["service_areas"]["exchange"]

                ## Input validation: ensure value is boolean
                if type(json_data["service_areas"]["exchange"]) != bool:
                    raise Exception('Service Areas "exchange" value must be a Boolean True or False. [1011]')
                    sys.exit(1)
            else:
                ## Default False
                json_data["service_areas"]["exchange"] = False

            ## service_areas:sharepoint
            if "sharepoint" in jsonstr["service_areas"]:
                json_data["service_areas"]["sharepoint"] = jsonstr["service_areas"]["sharepoint"]

                ## Input validation: ensure value is boolean
                if type(json_data["service_areas"]["sharepoint"]) != bool:
                    raise Exception('Service Areas "sharepoint" value must be a Boolean True or False. [1012]')
                    sys.exit(1)
            else:
                ## Default False
                json_data["service_areas"]["sharepoint"] = False

            ## service_areas:skype
            if "skype" in jsonstr["service_areas"]:
                json_data["service_areas"]["skype"] = jsonstr["service_areas"]["skype"]

                ## Input validation: ensure value is boolean
                if type(json_data["service_areas"]["skype"]) != bool:
                    raise Exception('Service Areas "skype" value must be a Boolean True or False. [1017]')
                    sys.exit(1)
            else:
                ## Default False
                json_data["service_areas"]["skype"] = False
        else:
            ## No service_areas block defined, set defaults
            json_data["service_areas"]["common"] = True
            json_data["service_areas"]["exchange"] = False
            json_data["service_areas"]["sharepoint"] = False
            json_data["service_areas"]["skype"] = False

        ## outputs
        if "outputs" in jsonstr:

            ## outputs:url_categories
            if "url_categories" in jsonstr["outputs"]:
                json_data["outputs"]["url_categories"] = jsonstr["outputs"]["url_categories"]

                ## Input validation: ensure value is boolean
                if type(json_data["outputs"]["url_categories"]) != bool:
                    raise Exception('Outputs "url_categories" value must be a Boolean True or False. [1019]')
                    sys.exit(1)
            else:
                ## Default True
                json_data["outputs"]["url_categories"] = True

            ## outputs:url_datagroups
            if "url_datagroups" in jsonstr["outputs"]:
                json_data["outputs"]["url_datagroups"] = jsonstr["outputs"]["url_datagroups"]

                ## Input validation: ensure value is boolean
                if type(json_data["outputs"]["url_datagroups"]) != bool:
                    raise Exception('Outputs "url_datagroups" value must be a Boolean True or False. [1010]')
                    sys.exit(1)
            else:
                ## Default False
                json_data["outputs"]["url_datagroups"] = False

            ## outputs:ip_datagroups
            if "ip_datagroups" in jsonstr["outputs"]:
                json_data["outputs"]["ip_datagroups"] = jsonstr["outputs"]["ip_datagroups"]

                ## Input validation: ensure value is boolean
                if type(json_data["outputs"]["ip_datagroups"]) != bool:
                    raise Exception('Outputs "ip_datagroups" value must be a Boolean True or False. [1037]')
                    sys.exit(1)
            else:
                ## Default False
                json_data["outputs"]["ip_datagroups"] = False

        else:
            ## No outputs block defined, set defaults
            json_data["outputs"]["url_categories"] = True
            json_data["outputs"]["url_datagroups"] = False
            json_data["outputs"]["ip_datagroups"] = True

        ## o365_categories
        if "o365_categories" in jsonstr:

            ## o365_categories:all
            if "all" in jsonstr["o365_categories"]:
                json_data["o365_categories"]["all"] = jsonstr["o365_categories"]["all"]

                ## Input validation: ensure value is boolean
                if type(json_data["o365_categories"]["all"]) != bool:
                    raise Exception('O365 Categories "all" value must be a Boolean True or False. [1013]')
                    sys.exit(1)
            else:
                ## Default True
                json_data["o365_categories"]["all"] = True

            ## o365_categories:optimize
            if "optimize" in jsonstr["o365_categories"]:
                json_data["o365_categories"]["optimize"] = jsonstr["o365_categories"]["optimize"]

                ## Input validation: ensure value is boolean
                if type(json_data["o365_categories"]["optimize"]) != bool:
                    raise Exception('O365 Categories "optimize" value must be a Boolean True or False. [1026]')
                    sys.exit(1)
            else:
                ## Default False
                json_data["o365_categories"]["optimize"] = False

            ## o365_categories:default
            if "default" in jsonstr["o365_categories"]:
                json_data["o365_categories"]["default"] = jsonstr["o365_categories"]["default"]

                ## Input validation: ensure value is boolean
                if type(json_data["o365_categories"]["default"]) != bool:
                    raise Exception('O365 Categories "default" value must be a Boolean True or False. [1027]')
                    sys.exit(1)
            else:
                ## Default False
                json_data["o365_categories"]["default"] = False

            ## o365_categories:allow
            if "allow" in jsonstr["o365_categories"]:
                json_data["o365_categories"]["allow"] = jsonstr["o365_categories"]["allow"]

                ## Input validation: ensure value is boolean
                if type(json_data["o365_categories"]["allow"]) != bool:
                    raise Exception('O365 Categories "allow" value must be a Boolean True or False. [1028]')
                    sys.exit(1)
            else:
                ## Default False
                json_data["o365_categories"]["allow"] = False
        else:
            ## No o365_categories block defined, set defaults
            json_data["o365_categories"]["all"] = True
            json_data["o365_categories"]["optimize"] = False
            json_data["o365_categories"]["default"] = False
            json_data["o365_categories"]["allow"] = False

        ## only_required
        if "only_required" in jsonstr:
            json_data["only_required"] = jsonstr["only_required"]

            ## Input validation: ensure value is boolean
            if type(json_data["only_required"]) != bool:
                raise Exception('The "only_required" value must be a Boolean True or False. [1029]')
                sys.exit(1)
        else:
            ## Default True
            json_data["only_required"] = True

        ## excluded_urls
        if "excluded_urls" in jsonstr:
            json_data["excluded_urls"] = self.url_parser(jsonstr["excluded_urls"])
        else:
            ## Default []
            json_data["excluded_urls"] = []

        ## included_urls
        if "included_urls" in jsonstr:
            #json_data["included_urls"] = jsonstr["included_urls"]
            if "allow" in jsonstr["included_urls"]:
                json_data["included_urls"]["allow"] = self.url_parser(jsonstr["included_urls"]["allow"])
            if "optimized" in jsonstr["included_urls"]:
                json_data["included_urls"]["optimized"] = self.url_parser(jsonstr["included_urls"]["optimized"])
            if "default" in jsonstr["included_urls"]:
                json_data["included_urls"]["default"] = self.url_parser(jsonstr["included_urls"]["default"])
            if "all" in jsonstr["included_urls"]:
                json_data["included_urls"]["all"] = self.url_parser(jsonstr["included_urls"]["all"])
        else:
            ## Default []
            json_data["included_urls"] = {}
            json_data["included_urls"]["allow"] = []
            json_data["included_urls"]["optimized"] = []
            json_data["included_urls"]["default"] = []
            json_data["included_urls"]["all"] = []

        ## excluded_ips
        if "excluded_ips" in jsonstr:
            json_data["excluded_ips"] = jsonstr["excluded_ips"]
        else:
            ## Default []
            json_data["excluded_ips"] = []

        ## system
        if "system" in jsonstr:

            ## system:log_level
            if "log_level" in jsonstr["system"]:
                json_data["system"]["log_level"] = jsonstr["system"]["log_level"]

                ## Input validation: ensure value is an integer
                if type(json_data["system"]["log_level"]) != int:
                    raise Exception('The System "log level" value must be an integer between 0 and 2. [1018]')
                    sys.exit(1)

                ## Input validation: ensure value is an integer between 0 and 2
                if json_data["system"]["log_level"] < 0 or json_data["system"]["log_level"] > 2:
                    raise Exception('The System "log level" value must be an integer between 0 and 2. [1031]')
                    sys.exit(1)
            else:
                ## Default 1
                json_data["system"]["log_level"] = 1

            ## system:ca_bundle
            if "ca_bundle" in jsonstr["system"]:
                json_data["system"]["ca_bundle"] = jsonstr["system"]["ca_bundle"]
            else:
                ## Default ca-bundle.crt
                json_data["system"]["ca_bundle"] = "ca-bundle.crt"

            ## system:working_directory
            if "working_directory" in jsonstr["system"]:
                json_data["system"]["working_directory"] = jsonstr["system"]["working_directory"]
            else:
                ## Default "/shared/o365"
                json_data["system"]["working_directory"] = "/shared/o365"

            ## system:retry_attempts
            if "retry_attempts" in jsonstr["system"]:

                ## Input validation: ensure value is an integer
                if type(json_data["system"]["retry_attempts"]) != int:
                    raise Exception('The System "retry_attempts" value must be an integer. [1040]')
                    sys.exit(1)

                ## Input validation: ensure value is an integer 0 or higher
                if json_data["system"]["retry_attempts"] < 0:
                    raise Exception('The System "retry_attemps" value must be an integer 0 or higher. A 0 value disables retry attempts. [1041]')
                    sys.exit(1)

                json_data["system"]["retry_attempts"] = jsonstr["system"]["retry_attempts"]
            else:
                ## Default 3 retry attempts
                json_data["system"]["retry_attempts"] = 3

            ## system:retry_delay
            if "retry_delay" in jsonstr["system"]:

                ## Input validation: ensure value is an integer
                if type(json_data["system"]["retry_delay"]) != int:
                    raise Exception('The System "retry_delay" value must be an integer. [1042]')
                    sys.exit(1)

                ## Input validation: ensure value is an integer 0 or higher
                if json_data["system"]["retry_delay"] < 0:
                    raise Exception('The System "retry_delay" value must be an integer 0 (seconds) or higher. [1043]')
                    sys.exit(1)

                json_data["system"]["retry_delay"] = jsonstr["system"]["retry_delay"]
            else:
                ## Default 300 seconds retry delay
                json_data["system"]["retry_delay"] = 300

        else:
            ## No system block defined, set defaults
            json_data["system"]["log_level"] = 1
            json_data["system"]["ca_bundle"] = "ca-bundle.crt"
            json_data["system"]["working_directory"] = "/shared/o365"
            json_data["system"]["retry_attempts"] = 3
            json_data["system"]["retry_delay"] = 300

        ## schedule
        if "schedule" in jsonstr:

            ## schedule:periods
            if "periods" in jsonstr["schedule"]:
                json_data["schedule"]["periods"] = jsonstr["schedule"]["periods"]

                ## Input validation: ensure value is one of: monthly, weekly
                if json_data["schedule"]["periods"] not in {"monthly", "weekly", "daily", "none"}:
                    raise Exception('The Schedule "periods" value must be one of: \"monthly\", \"weekly\", \"daily\", or \"none\". [1020]')
                    sys.exit(1)
            else:
                ## Default none
                json_data["schedule"]["periods"] = "none"

            ## schedule:run_date
            if "run_date" in jsonstr["schedule"]:
                json_data["schedule"]["run_date"] = jsonstr["schedule"]["run_date"]

                if json_data["schedule"]["run_date"] == "":
                    ## Value empty, set default 1
                    json_data["schedule"]["run_date"] = 1

                ## Input validation: validate weekly/monthly values
                elif json_data["schedule"]["periods"] == "monthly":
                    ## Input validation: ensure run_date is an integer
                    if type(json_data["schedule"]["run_date"]) != int:
                        raise Exception('Schedule "run_date" value for period(monthly) must be an integer between 1 and 31. [1016]')
                        sys.exit(1)

                    ## Input validation: ensure monthly run_date is a value between 1 and 31
                    if json_data["schedule"]["run_date"] <= 0 or json_data["schedule"]["run_date"] > 31:
                        raise Exception('Schedule "run_date" value for period(monthly) must be an integer between 1 and 31. [1008]')
                        sys.exit(1)

                elif json_data["schedule"]["periods"] == "weekly":
                    ## Input validation: ensure run_date is an integer
                    if type(json_data["schedule"]["run_date"]) != int:
                        raise Exception('Schedule "run_date" value for period(weekly) must be an integer between 0 (Sunday) and 6 (Saturday). [1025]')
                        sys.exit(1)

                    ## Input validation: ensure weekly run_date is a value between 1 and 7
                    if json_data["schedule"]["run_date"] < 0 or json_data["schedule"]["run_date"] > 6:
                        raise Exception('Schedule "run_date" value for period(weekly) must be an integer between 0 (Sunday) and 6 (Saturday). [1030]')
                        sys.exit(1)

            else:
                ## Default 1
                json_data["schedule"]["run_date"] = 1

            ## schedule:run_time
            if "run_time" in jsonstr["schedule"]:
                json_data["schedule"]["run_time"] = jsonstr["schedule"]["run_time"]

                if json_data["schedule"]["run_time"] == "":
                    ## Value empty, set default "04:00"
                    json_data["schedule"]["run_time"] = "04:00"

                ## Input validation: ensure correct time format
                elif not re.match(r"[0-9]{1,2}:[0-9]{2}", json_data["schedule"]["run_time"]):
                    raise Exception('Schedule "run_time" value must be a valid 24-hour time (ex. 14:30). [1033]')
                    sys.exit(1)

                ## Input validation: ensure first number (hour) between 0 and 23, and second number (minutes) between 0 and 59
                this_time = json_data["schedule"]["run_time"].split(":")
                if int(this_time[0]) < 0 or int(this_time[0]) > 23:
                    raise Exception('Schedule "run_time" hour value must be a valid 24-hour integer between 0 and 23. [1038]')
                    sys.exit(1)
                if int(this_time[1]) < 0 or int(this_time[1]) > 59:
                    raise Exception('Schedule "run_time" minute value must be a valid integer between 0 and 59. [1022]')
                    sys.exit(1)
            else:
                ## Default "04:00"
                json_data["schedule"]["run_time"] = "04:00"

            ## schedule:start_date
            if "start_date" in jsonstr["schedule"]:
                json_data["schedule"]["start_date"] = jsonstr["schedule"]["start_date"]

                if json_data["schedule"]["start_date"] == "":
                    pass

                ## Input validation: ensure correct m/d/Y format
                elif not re.match(r"[0-9]{1,2}\/[0-9]{1,2}\/[0-9]{4}", json_data["schedule"]["start_date"]):
                    raise Exception('Schedule "start_date" value must be in month/day/year format (ex. 03/29/2021). [1023]')
                    sys.exit(1)
            else:
                ## Default ""
                json_data["schedule"]["start_date"] = ""

            ## schedule:start_time
            if "start_time" in jsonstr["schedule"]:
                json_data["schedule"]["start_time"] = jsonstr["schedule"]["start_time"]

                if json_data["schedule"]["start_time"] == "":
                    pass

                ## Input validation: ensure correct time format
                elif not re.match(r"[0-9]{1,2}:[0-9]{2}", json_data["schedule"]["start_time"]):
                    raise Exception('Schedule "start_time" value must be a valid 24-hour time (ex. 14:30). [1034]')
                    sys.exit(1)

                ## Input validation: ensure first number (hour) between 0 and 23, and second number (minutes) between 0 and 59
                else:
                    this_time = json_data["schedule"]["start_time"].split(":")
                    if int(this_time[0]) < 0 or int(this_time[0]) > 23:
                        raise Exception('Schedule "start_time" hour value must be a valid 24-hour integer between 0 and 23. [1035]')
                        sys.exit(1)
                    if int(this_time[1]) < 0 or int(this_time[1]) > 59:
                        raise Exception('Schedule "start_time" minute value must be a valid integer between 0 and 59. [1036]')
                        sys.exit(1)
            else:
                ## Default ""
                json_data["schedule"]["start_time"] = ""
        else:
            ## No schedule block defined, set defaults
            json_data["schedule"]["periods"] = "none"
            json_data["schedule"]["run_date"] = 1
            json_data["schedule"]["run_time"] = "04:00"
            json_data["schedule"]["start_date"] = ""
            json_data["schedule"]["start_time"] = ""

        return(json_data)


    ##-----------------------------------------------------------------------
    ## addLastRun function
    ##  Purpose: update last_run information in the JSON iFile data (assumes config is loaded)
    ##  Parameters:
    ##      datestr         = datetime string
    ##      reason          = message to insert
    ##-----------------------------------------------------------------------
    def addLastRun(self, datestr, reason, isHashedValuesChanged=False, updatedHashedValues={}):
        # Find all versions of the configuration iFile
        o365_config = ""
        entry_array = []
        fileList = os.listdir('/config/filestore/files_d/Common_d/ifile_d/')
        pattern = "*o365_config.json*"
        for entry in fileList:
            if fnmatch.fnmatch(entry, pattern):
                entry_array.append("/config/filestore/files_d/Common_d/ifile_d/" + entry)

        ## Get JSON data from configuration file and update with last_run information
        o365_config = max(entry_array, key=os.path.getctime)
        f = open(o365_config, "r")
        f_content = f.read()
        f.close()
        config_data = json.loads(f_content)
        #if URl updates are successful and hashvalues are changed from last run then update these new hashed values in json
        if isHashedValuesChanged:
            config_data["status"] = updatedHashedValues

        config_data["status"]["last_run"] = str(datestr)
        config_data["status"]["description"] = reason

        ## Convert updated JSON data to formatted string
        json_config_final = json.dumps(config_data, indent = 4)

        ## Write updated JSON data to a temporary file
        with open(config_data["system"]["working_directory"] + "/config.json", "w") as outfile:
            outfile.write(json_config_final)

        ## Update the ifile configuration / delete temporary file
        result = shell.getoutput("tmsh -a modify sys file ifile o365_update.app/o365_config.json source-path file:" + config_data["system"]["working_directory"] + "/config.json")
        os.remove(config_data["system"]["working_directory"] + "/config.json")


    ##-----------------------------------------------------------------------
    ## Create URL categories function
    ##  Purpose: creates O365 URL categories from supplied URL information
    ##  Parameters:
    ##      url_file        = name of the URL category
    ##      url_list        = list of URLs
    ##      version_latest  = latest version string
    ##  Example:
    ##      self.create_url_categories (o365_category, urls_undup, ms_o365_version_latest)
    ##-----------------------------------------------------------------------
    def create_url_categories (self, url_file, url_list, version_latest):
        ## Initialize the url string
        str_urls_to_bypass = ""

        ## Create new or clean out existing URL category - add the latest version as first entry
        result = shell.getoutput("tmsh -a list sys application service o365_update.app/o365_update")
        if "was not found" in result:
            result2 = shell.getoutput("tmsh -a create sys application service o365_update traffic-group traffic-group-local-only device-group none")
            self.log(2, self.log_level, self.logdir, "Application service not found. Creating o365_update.app/o365_update")

        result = shell.getoutput("tmsh -a list sys url-db url-category o365_update.app/" + url_file)
        if "was not found" in result:
            result2 = shell.getoutput("tmsh -a create /sys url-db url-category o365_update.app/" + url_file + " display-name " + url_file + " app-service o365_update.app/o365_update urls replace-all-with { https://" + version_latest + "/ { type exact-match } } default-action allow")
            self.log(2, self.log_level, self.logdir, "O365 custom URL category (" + url_file + ") not found. Created new O365 custom category.")
        else:
            result2 = shell.getoutput("tmsh -a modify /sys url-db url-category o365_update.app/" + url_file + " display-name " + url_file + " app-service o365_update.app/o365_update urls replace-all-with { https://" + version_latest + "/ { type exact-match } } default-action allow")
            self.log(2, self.log_level, self.logdir, "O365 custom URL category (" + url_file + ") exists. Clearing entries for new data.")

        ## Loop through URLs and insert into URL category
        for url in url_list:
            ## Force URL to lower case
            url = url.lower()

            ## Add * if url starts with "." (if a wildcard included_url is added)
            if url.startswith("."):
                url = "*" + url

            ## If URL starts with an asterisk, set as a glob-match URL, otherwise exact-match. Send to a string.
            if ('*' in url):
                ## Escaping any asterisk characters
                url_processed = re.sub('\*', '\\*', url)
                str_urls_to_bypass = str_urls_to_bypass + " urls add { \"https://" + url_processed + "/\" { type glob-match } } urls add { \"http://" + url_processed + "/\" { type glob-match } }"
            else:
                str_urls_to_bypass = str_urls_to_bypass + " urls add { \"https://" + url + "/\" { type exact-match } } urls add { \"http://" + url + "/\" { type exact-match } }"

        ## Import the URL entries
        result = shell.getoutput("tmsh -a modify /sys url-db url-category o365_update.app/" + url_file + " app-service o365_update.app/o365_update" + str_urls_to_bypass)


    ##-----------------------------------------------------------------------
    ## Create URL datagroups function
    ##  Purpose: creates O365 URL datagroups from supplied URL information
    ##  Parameters:
    ##      url_file        = name of the URL datagroup
    ##      url_list        = list of URLs
    ##  Example:
    ##      self.create_url_datagroups (o365_dg, urls_undup)
    ##-----------------------------------------------------------------------
    def create_url_datagroups (self, url_file, url_list):
        ## Write data to a file for import into data group
        fout = open(self.work_directory + "/" + url_file, 'w')
        for url in (list(sorted(set(url_list)))):
            ## Replace any asterisk characters with a dot
            url_processed = re.sub('\*', '', url)
            fout.write("\"" + str(url_processed.lower()) + "\" := \"\",\n")
        fout.flush()
        fout.close()

        ## Create URL data group files in TMSH if they don't already exist
        result = shell.getoutput("tmsh -a list sys application service o365_update.app/o365_update")
        if "was not found" in result:
            result2 = shell.getoutput("tmsh -a create sys application service o365_update traffic-group traffic-group-local-only device-group none")
            self.log(2, self.log_level, self.logdir, "Application service not found. Creating o365_update.app/o365_update")

        result = shell.getoutput("tmsh -a list /sys file data-group o365_update.app/" + url_file)
        if "was not found" in result:
            ## Create (sys) external data group
            result2 = shell.getoutput("tmsh -a create /sys file data-group o365_update.app/" + url_file + " separator \":=\" source-path file:" + self.work_directory + "/" + url_file + " type string")
            ## Create (ltm) link to external data group
            result3 = shell.getoutput("tmsh -a create /ltm data-group external o365_update.app/" + url_file + " external-file-name o365_update.app/" + url_file)
            self.log(2, self.log_level, self.logdir, "O365 URL data group (" + url_file + ") not found. Created new data group.")
        else:
            ## Update (sys) external data group
            result2 = shell.getoutput("tmsh -a modify /sys file data-group o365_update.app/" + url_file + " source-path file:" + self.work_directory + "/" + url_file)
            ## Update (ltm) link to external data group
            result3 = shell.getoutput("tmsh -a create /ltm data-group external o365_update.app/" + url_file + " external-file-name o365_update.app/" + url_file)
            self.log(2, self.log_level, self.logdir, "O365 URL data group (" + url_file + ") exists. Updated existing data group.")

        os.remove(self.work_directory + "/" + url_file)


    ##-----------------------------------------------------------------------
    ## Create IP datagroups function
    ##  Purpose: create IP datagroups from supplied IP addresses
    ##  Parameters:
    ##      url_file        = name of IP datagroup
    ##      url_list        = list of IP addresses
    ##  Example:
    ##      self.create_ip_datagroups (o365_dg_ipv4, ipv4_undup)
    ##-----------------------------------------------------------------------
    def create_ip_datagroups (self, url_file, url_list):
        ## Write data to a file for import into data group
        fout = open(self.work_directory + "/" + url_file, 'w')
        for ip in (list(sorted(url_list))):
            fout.write("network " + str(ip) + ",\n")
        fout.flush()
        fout.close()

        ## Create URL data group files in TMSH if they don't already exist
        result = shell.getoutput("tmsh -a list sys application service o365_update.app/o365_update")
        if "was not found" in result:
            result2 = shell.getoutput("tmsh -a create sys application service o365_update traffic-group traffic-group-local-only device-group none")
            self.log(2, self.log_level, self.logdir, "Application service not found. Creating o365_update.app/o365_update")

        result = shell.getoutput("tmsh -a list /sys file data-group o365_update.app/" + url_file)
        if "was not found" in result:
            result2 = shell.getoutput("tmsh -a create /sys file data-group o365_update.app/" + url_file + " source-path file:" + self.work_directory + "/" + url_file + " type ip")
            result3 = shell.getoutput("tmsh -a create /ltm data-group external o365_update.app/" + url_file + " external-file-name o365_update.app/" + url_file)
            self.log(2, self.log_level, self.logdir, "O365 IP data group (" + url_file + ") not found. Created new data group.")
        else:
            result2 = shell.getoutput("tmsh -a modify /sys file data-group o365_update.app/" + url_file + " source-path file:" + self.work_directory + "/" + url_file)
            result3 = shell.getoutput("tmsh -a create /ltm data-group external o365_update.app/" + url_file + " external-file-name o365_update.app/" + url_file)
            self.log(2, self.log_level, self.logdir, "O365 IP data group (" + url_file + ") exists. Updated existing data group.")

        os.remove(self.work_directory + "/" + url_file)


    ##-----------------------------------------------------------------------
    ## URL fetch function
    ##  Purpose: generate an HTTP request to O365 API and return resulting JSON
    ##  Parameters:
    ##      req_string      = request URL
    ##-----------------------------------------------------------------------
    def url_fetch(self, req_string):
        # we don't pass --force to cron, so force_update comes from user or update worker, try only once
        if self.retry_attempts > 0 and not self.force_update:
            attempts = self.retry_attempts - 1
        else:
            attempts = 0

        def sleep(attempts):
            if attempts >= 0:
                time.sleep(self.retry_delay)

        count = 1
        error = ""
        while attempts >= 0:
            attempts -= 1
            try:
                if self.proxyip != None:
                    localproxy = 'http://' + self.proxyip + ':' + str(self.proxyport)
                    proxyctl = urlrequest.ProxyHandler({'https': localproxy,'http': localproxy})
                    context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH, cafile=self.cafile)
                    handler = urlrequest.HTTPSHandler(context=context)
                    opener = urlrequest.build_opener(handler, proxyctl)
                    urlrequest.install_opener(opener)
                    res = urlrequest.urlopen(req_string)
                else:
                    context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH, cafile=self.cafile)
                    handler = urlrequest.HTTPSHandler(context=context)
                    opener = urlrequest.build_opener(handler)
                    urlrequest.install_opener(opener)
                    res = urlrequest.urlopen(req_string)

            except urlrequest.URLError as e:
                present = datetime.datetime.now()
                self.log(1, self.log_level, self.logdir, "ERROR: Attempt (" + str(count) + ") to request O365 information failed (1004): " + str(e.reason) + "\n")
                self.event_log(1, "ERROR: Attempt (" + str(count) + ") to request O365 information failed (1004): " + str(e.reason) + "\n")
                self.addLastRun(present.strftime("%Y-%m-%d %H:%M"), "ERROR: Attempt (" + str(count) + ") to request O365 information failed (1004): " + str(e.reason) + "\n")
                sys.stderr.write("ERROR: Attempt (" + str(count) + ") to request O365 information failed (1004): " + str(e.reason) + "\n")
                count += 1
                error = str(e.reason)
                sleep(attempts)
                continue

            except Exception as e:
                present = datetime.datetime.now()
                self.log(1, self.log_level, self.logdir, "ERROR: Attempt (" + str(count) + ") to request O365 information failed (1005): " + str(e.reason))
                self.event_log(1, "ERROR: Attempt (" + str(count) + ") to request O365 information failed (1005): " + str(e.reason))
                self.addLastRun(present.strftime("%Y-%m-%d %H:%M"), "ERROR: Attempt (" + str(count) + ") to request O365 information failed (1005): " + str(e.reason))
                sys.stderr.write("ERROR: Attempt (" + str(count) + ") to request O365 information failed (1005): " + str(e.reason) + "\n")
                count += 1
                error = str(e.reason)
                sleep(attempts)
                continue

            if res.getcode() != 200:
                present = datetime.datetime.now()
                self.log(1, self.log_level, self.logdir, "ERROR: Attempt (" + str(count) + ") to request O365 information failed (1006): " + str(e.reason))
                self.event_log(1, "ERROR: Attempt (" + str(count) + ") to request O365 information failed (1006): " + str(e.reason))
                self.addLastRun(present.strftime("%Y-%m-%d %H:%M"), "ERROR: Attempt (" + str(count) + ") to request O365 information failed (1006): " + str(e.reason))
                sys.stderr.write("ERROR: Attempt (" + str(count) + ") to request O365 information failed (1006): " + str(e.reason) + "\n")
                count += 1
                error = str(e.reason)
                sleep(attempts)
                continue
            else:
                ## Looks good - return response
                return res

        present = datetime.datetime.now()
        self.log(1, self.log_level, self.logdir, "ERROR: Failed all attempts to request O365 information. Aborting until next scheduled run. " + error)
        self.event_log(1, "ERROR: Failed all attempts to request O365 information. Aborting until next scheduled run. " + error)
        self.addLastRun(present.strftime("%Y-%m-%d %H:%M"), "ERROR: Failed all attempts to request O365 information. Aborting until next scheduled run. " + error)
        sys.stderr.write("ERROR: Failed all attempts to request O365 information. Aborting until next scheduled run. " + error + "\n")
        sys.exit(1)


    ##-----------------------------------------------------------------------
    ## Update O365 function
    ##  Purpose: main work function. Processes O365 URLs and updates URL categories and datagroups
    ##  Parameters: none
    ##-----------------------------------------------------------------------
    def update_o365(self):

        list_urls_to_bypass = []
        list_optimized_urls_to_bypass = []
        list_default_urls_to_bypass = []
        list_allow_urls_to_bypass = []
        list_ipv4_to_pbr = []
        list_ipv6_to_pbr = []

        self.get_config()
        if self.work_directory != "":

            ## -----------------------------------------------------------------------
            ## Scheduling:
            ## - /etc/cron.d/0hourly manages the frequency (periods, run_date, run_time)
            ## - Make sure here that current date/time >= start_data, start_time
            ## - If no start_date/start_time defined, just proceed
            ## -----------------------------------------------------------------------
            if self.schedule_start_date != "":
                ## start_date/start_time defined - process datetime logic
                if self.schedule_start_time == "":
                    self.schedule_start_time != "00:00"

                ## Extract day, month, year, hour, minute from start_date and start_time
                inmonth, inday, inyear = [int(x) for x in self.schedule_start_date.split('/')]
                inhour, inminute = [int(x) for x in self.schedule_start_time.split(':')]

                ## Define start and current datetimes
                start = datetime.datetime(inyear, inmonth, inday, inhour, inminute, 0)
                present = datetime.datetime.now()

                ## If start is > current datetime, do not proceed
                if start > present:
                    self.log(1, self.log_level, self.logdir, "Defined start date/time greater than current time - Aborting (1003).")
                    sys.exit()


            ## -----------------------------------------------------------------------
            ## System Proxy Detection (System : Configuration : Devices : Upstream Proxy)
            ## -----------------------------------------------------------------------
            result = shell.getoutput("tmsh -a list sys management-proxy-config proxy-ip-addr proxy-port")
            if result != "":
                for line in result.split('\n'):
                    if "proxy-ip-addr" in line:
                        self.proxyip = line.strip().split()[1]
                    if "proxy-port" in line:
                        self.proxyport = line.strip().split()[1]

                ## Test if the proxyport is an integer or (string) service name
                try:
                    self.proxyport = int(self.proxyport)
                except:
                    ## proxyport is a string service name - resolve to port number
                    result = shell.getoutput("getent services " + self.proxyport)
                    result = re.sub('.*\s(\d+)\/.*', r'\1', result)
                    self.proxyport = int(result)

            else:
                self.proxyip = None
                self.proxyport = None


            ## -----------------------------------------------------------------------
            ## System CA bundle selection (defaults to ca-bundle.crt if none selected)
            ## -----------------------------------------------------------------------
            result = shell.getoutput("tmsh -a list sys file ssl-cert " + self.ca_bundle + " system-path")
            if result != "":
                for line in result.split('\n'):
                    if "system-path" in line:
                        self.cafile = line.strip().split()[1]
            else:
                self.cafile = "ca-bundle.crt"


            ## -----------------------------------------------------------------------
            ## GUID management
            ## -----------------------------------------------------------------------
            ## Create the guid file if it doesn't exist
            if not os.path.isdir(self.work_directory):
                os.mkdir(self.work_directory)
                self.log(1, self.log_level, self.logdir, "Created work directory " + self.work_directory + " because it did not exist.")
            if not os.path.exists(self.work_directory + "/guid.txt"):
                f = open(self.work_directory + "/guid.txt", "w")
                f.write("\n")
                f.flush()
                f.close()
                self.log(1, self.log_level, self.logdir, "Created GUID file " + self.work_directory + "/guid.txt because it did not exist.")

            ## Read guid from file and validate.  Create one if not existent
            f = open(self.work_directory + "/guid.txt", "r")
            f_content = f.readline()
            f.close()
            if re.match('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', f_content):
                guid = f_content
                self.log(2, self.log_level, self.logdir, "Valid GUID is read from local file " + self.work_directory + "/guid.txt.")
            else:
                guid = str(uuid.uuid4())
                f = open(self.work_directory + "/guid.txt", "w")
                f.write(guid)
                f.flush()
                f.close()
                self.log(1, self.log_level, self.logdir, "Generated a new GUID, and saved it to " + self.work_directory + "/guid.txt.")


            ## -----------------------------------------------------------------------
            ## O365 endpoints list version check
            ## -----------------------------------------------------------------------
            ## Ensure that a local version exists
            if os.path.isfile(self.work_directory + "/o365_version.txt"):
                f = open(self.work_directory + "/o365_version.txt", "r")
                f_content = f.readline()
                f.close()
                ## Check if the VERSION record format is valid
                if re.match('[0-9]{10}', f_content):
                    ms_o365_version_previous = f_content
                    self.log(2, self.log_level, self.logdir, "Valid previous VERSION found in " + self.work_directory + "/o365_version.txt.")
                else:
                    ms_o365_version_previous = "1970010200"
                    f = open(self.work_directory + "/o365_version.txt", "w")
                    f.write(ms_o365_version_previous)
                    f.flush()
                    f.close()
                    self.log(1, self.log_level, self.logdir, "Valid previous VERSION was not found.  Wrote dummy value in " + self.work_directory + "/o365_version.txt.")
            else:
                ms_o365_version_previous = "1970010200"
                f = open(self.work_directory + "/o365_version.txt", "w")
                f.write(ms_o365_version_previous)
                f.flush()
                f.close()
                self.log(1, self.log_level, self.logdir, "Valid previous VERSION was not found.  Wrote dummy value in " + self.work_directory + "/o365_version.txt.")


            ## -----------------------------------------------------------------------
            ## O365 endpoints list VERSION check
            ## -----------------------------------------------------------------------
            ## Read the version of previously received records. If different than stored information, then data is assumed new/changed
            request_string = uri_ms_o365_version + guid
            req_string = "https://" + url_ms_o365_version + request_string

            ## Call url_fetch function
            res = self.url_fetch(req_string)

            try:
                ## Data fetched - validate and convert to JSON
                dict_o365_version = json.loads(res.read())
                self.log(2, self.log_level, self.logdir, "VERSION request to MS web service was successful.")
                self.event_log(2, "VERSION request to MS web service was successful.")
            except Exception as e:
                present = datetime.datetime.now()
                self.log(2, self.log_level, self.logdir, "Error: Good response but invalid (non-JSON) data encountered. Aborting (1007): " + str(e))
                self.event_log(2, "Error: Good response but invalid (non-JSON) data encountered. Aborting (1007): " + str(e))
                self.addLastRun(present.strftime("%Y-%m-%d %H:%M"), "Error: Good response but invalid (non-JSON) data encountered. Aborting (1007): " + str(e))
                sys.stderr.write("ERROR: Good response but invalid (non-JSON) data encountered. Aborting (1007): " + str(e) + "\n")
                sys.exit(1)

            ms_o365_version_latest = ""
            for record in dict_o365_version:
                if 'instance' in record :
                    if record["instance"] == self.customer_endpoint and "latest" in record:
                        latest = record["latest"]
                        if re.match('[0-9]{10}', latest):
                            ms_o365_version_latest = latest
                            f = open(self.work_directory + "/o365_version.txt", "w")
                            f.write(ms_o365_version_latest)
                            f.flush()
                            f.close()

            self.log(2, self.log_level, self.logdir, "Previous VERSION is " + ms_o365_version_previous)
            self.log(2, self.log_level, self.logdir, "Latest VERSION is " + ms_o365_version_latest)

            ## -----------------------------------------------------------------------
            ## check the hash of excluded IPs and excluded urls to check if they are changed, if yes, run the schdule
            ## -----------------------------------------------------------------------
            currentHash_excludeUrls = self.get_hashedValue(self.excluded_urls)
            currentHash_excludeIPs = self.get_hashedValue(self.excluded_ips)
            isExcludedUrlsSame = (currentHash_excludeUrls == self.status["last_hash_excludedUrls"])
            isExcludedIPsSame = (currentHash_excludeIPs == self.status["last_hash_excludedIPs"])

            # included_urls hash comparison
            currentHash_includedUrls = {}
            currentHash_includedUrls["default"] = self.get_hashedValue(self.included_urls_default)
            currentHash_includedUrls["all"] = self.get_hashedValue(self.included_urls_all)
            currentHash_includedUrls["optimized"] = self.get_hashedValue(self.included_urls_optimized)
            currentHash_includedUrls["allow"] = self.get_hashedValue(self.included_urls_allow)

            lastHash_values = self.status["last_hash_includedUrls"]
            if bool(lastHash_values) :
                isIncludedUrlsSame = currentHash_includedUrls["default"] == lastHash_values["default"] and\
                currentHash_includedUrls["all"] == lastHash_values["all"] and\
                currentHash_includedUrls["allow"] == lastHash_values["allow"] and\
                currentHash_includedUrls["optimized"] == lastHash_values["optimized"]
            else:
                isIncludedUrlsSame = False

            isHashedValuesSame = isIncludedUrlsSame and isExcludedUrlsSame and isExcludedIPsSame
            if not isHashedValuesSame:
                self.status["last_hash_includedUrls"] = currentHash_includedUrls
                self.status["last_hash_excludedUrls"] = currentHash_excludeUrls
                self.status["last_hash_excludedIPs"] = currentHash_excludeIPs
                updatedHashedValues = self.status

            # If there is no change in included_url, excluded_url and excluded_ip after last run and guid is also same then no need to run the fetcha again
            if ms_o365_version_latest == ms_o365_version_previous and isHashedValuesSame:
                present = datetime.datetime.now()
                self.log(1, self.log_level, self.logdir, "Latest MS O365 URL/IP Address list already exists: " + ms_o365_version_latest + ". Aborting at " + present.strftime("%Y-%m-%d %H:%M"))
                self.addLastRun(present.strftime("%Y-%m-%d %H:%M"), "URLs exists - update bypassed")
                sys.stderr.write("ERROR: Latest MS O365 URL/IP Address list already exists: " + ms_o365_version_latest + ". Aborting at " + present.strftime("%Y-%m-%d %H:%M") + "\n")
                sys.exit(1)

            elif self.force_update or isHashedValuesSame:
                self.log(1, self.log_level, self.logdir, "Command called with \"--force\" option. Manual update initiated.")
                pass

            ## -----------------------------------------------------------------------
            ## Request O365 endpoints list and store in dictionaries
            ## -----------------------------------------------------------------------
            ## Make the request to fetch JSON data from Microsoft
            request_string = "/endpoints/" + self.customer_endpoint + "?ClientRequestId=" + guid
            req_string = "https://" + url_ms_o365_endpoints + request_string

            ## Call url_fetch function
            res = self.url_fetch(req_string)

            try:
                ## Data fetched - validate and convert to JSON
                dict_o365_all = json.loads(res.read())
                self.log(2, self.log_level, self.logdir, "ENDPOINTS request to MS web service was successful.")
                self.event_log(2, "ENDPOINTS request to MS web service was successful.")
            except Exception as e:
                present = datetime.datetime.now()
                self.log(2, self.log_level, self.logdir, "Error: Good response but invalid (non-JSON) data encountered. Aborting (1024): " + str(e))
                self.event_log(2, "Error: Good response but invalid (non-JSON) data encountered. Aborting (1024): " + str(e))
                self.addLastRun(present.strftime("%Y-%m-%d %H:%M"), "Error: Good response but invalid (non-JSON) data encountered. Aborting (1024): " + str(e))
                sys.stderr.write("ERROR: Good response but invalid (non-JSON) data encountered. Aborting (1024): " + str(e) + "\n")
                sys.exit(1)


            ## Process for each record(id) of the endpoint JSON data - this churns the JSON data into separate URL lists
            for dict_o365_record in dict_o365_all:
                service_area = str(dict_o365_record['serviceArea'])
                id = str(dict_o365_record['id'])

                if (self.only_required == 0) or (self.only_required and str(dict_o365_record['required']) == "True"):

                    if (self.service_area_common and service_area == "Common") \
                        or (self.service_area_exchange and service_area == "Exchange") \
                        or (self.service_area_sharepoint and service_area == "SharePoint") \
                        or (self.service_area_skype and service_area == "Skype"):

                        if self.output_url_categories or self.output_url_datagroups:
                            ## Append "urls" if existent in each record (full list)
                            if self.o365_categories_all and 'urls' in dict_o365_record:
                                list_urls = list(dict_o365_record['urls'])
                                for url in list_urls:
                                    list_urls_to_bypass.append(url)

                            # Append "optimized" URLs if required (optimized list)
                            if self.o365_categories_optimize and 'urls' in dict_o365_record and 'category' in dict_o365_record and dict_o365_record['category'] == "Optimize":
                                list_optimized_urls = list(dict_o365_record['urls'])
                                for url in list_optimized_urls:
                                    list_optimized_urls_to_bypass.append(url)

                            # Append "default" URLs if required (default list)
                            if self.o365_categories_default and 'urls' in dict_o365_record and 'category' in dict_o365_record and dict_o365_record['category'] == "Default":
                                list_default_urls = list(dict_o365_record['urls'])
                                for url in list_default_urls:
                                    list_default_urls_to_bypass.append(url)

                            # Append "allow" URLs if required (allow list)
                            if self.o365_categories_allow and 'urls' in dict_o365_record and 'category' in dict_o365_record and dict_o365_record['category'] == "Allow":
                                list_allow_urls = list(dict_o365_record['urls'])
                                for url in list_allow_urls:
                                    list_allow_urls_to_bypass.append(url)

                        if self.output_ip_datagroups:
                            # Append "ips" if existent in each record
                            if 'ips' in dict_o365_record:
                                list_ips = list(dict_o365_record['ips'])
                                for ip in list_ips:
                                    if re.match('^.+:', ip):
                                        list_ipv6_to_pbr.append(ip)
                                    else:
                                        list_ipv4_to_pbr.append(ip)


            # -----------------------------------------------------------------------
            # Re-process URLs/IPs to add included urls (all-urls category)
            # -----------------------------------------------------------------------
            if self.output_url_categories or self.output_url_datagroups:
                # Append included_urls_all
                for url in self.included_urls_all:
                    list_urls_to_bypass.append(url)

                # Append included_urls_optimized
                for url in self.included_urls_optimized:
                    list_optimized_urls_to_bypass.append(url)

                # Append included_urls_default
                for url in self.included_urls_default:
                    list_default_urls_to_bypass.append(url)

                # Append included_urls_allow
                for url in self.included_urls_allow:
                    list_allow_urls_to_bypass.append(url)


            # -----------------------------------------------------------------------
            # Re-process URLs/IPs to remove duplicates and excluded values
            # -----------------------------------------------------------------------
            if self.output_url_categories or self.output_url_datagroups:
                # Remove duplicate URLs in the list (full list) and remove set of excluded URLs from the list of collected URLs

                # Full list
                if self.o365_categories_all:
                    urls_undup = list(set(list_urls_to_bypass))
                    for x_url in self.excluded_urls:
                        urls_undup = [x for x in urls_undup if not x.endswith(x_url)]

                # Optimized list
                if self.o365_categories_optimize:
                    urls_optimized_undup = list(set(list_optimized_urls_to_bypass))
                    for x_url in self.excluded_urls:
                        urls_optimized_undup = [x for x in urls_optimized_undup if not x.endswith(x_url)]

                # Default list
                if self.o365_categories_default:
                    urls_default_undup = list(set(list_default_urls_to_bypass))
                    for x_url in self.excluded_urls:
                        urls_default_undup = [x for x in urls_default_undup if not x.endswith(x_url)]

                # Allow list
                if self.o365_categories_allow:
                    urls_allow_undup = list(set(list_allow_urls_to_bypass))
                    for x_url in self.excluded_urls:
                        urls_allow_undup = [x for x in urls_allow_undup if not x.endswith(x_url)]


            if self.output_ip_datagroups:
                # Remove duplicate IPv4 addresses in the list
                ipv4_undup = list(set(list_ipv4_to_pbr))

                ## Remove set of excluded IPv4 addresses from the list of collected IPv4 addresses
                for x_ip in self.excluded_ips:
                    ipv4_undup = [x for x in ipv4_undup if not x.endswith(x_ip)]

                # Remove duplicate IPv6 addresses in the list
                ipv6_undup = list(set(list_ipv6_to_pbr))

                ## Remove set of excluded IPv6 addresses from the list of collected IPv6 addresses
                for x_ip in self.excluded_ips:
                    ipv6_undup = [x for x in ipv6_undup if not x.endswith(x_ip)]

            if not self.o365_categories_all:
                urls_undup = []

            if not self.output_ip_datagroups:
                ipv4_undup = []
                ipv6_undup = []

            self.log(1, self.log_level, self.logdir, "Number of unique ENDPOINTS to import : URL:" + str(len(urls_undup)) + ", IPv4 host/net:" + str(len(ipv4_undup)) + ", IPv6 host/net:" + str(len(ipv6_undup)))


            # -----------------------------------------------------------------------
            # O365 endpoint URLs re-formatted to fit into custom URL categories and/or data groups
            # -----------------------------------------------------------------------
            # This generates the temp files, data groups, and URL categories
            if self.output_url_categories or self.output_url_datagroups:

                if self.output_url_categories:
                    if self.o365_categories_all:
                        self.create_url_categories (o365_category, urls_undup, ms_o365_version_latest)

                    if self.o365_categories_optimize:
                        self.create_url_categories (o365_category_optimized, urls_optimized_undup, ms_o365_version_latest)

                    if self.o365_categories_default:
                        self.create_url_categories (o365_category_default, urls_default_undup, ms_o365_version_latest)

                    if self.o365_categories_allow:
                        self.create_url_categories (o365_category_allow, urls_allow_undup, ms_o365_version_latest)

                if self.output_url_datagroups:
                    if self.o365_categories_all:
                        self.create_url_datagroups (o365_dg, urls_undup)

                    if self.o365_categories_optimize:
                        self.create_url_datagroups (o365_dg_optimize, urls_optimized_undup)

                    if self.o365_categories_default:
                        self.create_url_datagroups (o365_dg_default, urls_default_undup)

                    if self.o365_categories_allow:
                        self.create_url_datagroups (o365_dg_allow, urls_allow_undup)

            if self.output_ip_datagroups:
                self.create_ip_datagroups (o365_dg_ipv4, ipv4_undup)
                self.create_ip_datagroups (o365_dg_ipv6, ipv6_undup)

            if self.force_update:
                forcebool = "True"
            else:
                forcebool = "False"

            present = datetime.datetime.now()
            self.log(1, self.log_level, self.logdir, "Completed O365 URL/IP address update process (force update: " + forcebool + "). Last run at: " + present.strftime("%Y-%m-%d %H:%M"))
            self.addLastRun(present.strftime("%Y-%m-%d %H:%M"), "O365 URLs are updated successfully.", not isHashedValuesSame, updatedHashedValues)
            print("[force-success]O365 URLs/IP Addresses are updated successfully.")


    ##-----------------------------------------------------------------------
    ## Install script function
    ##  Purpose: install the script and configuration
    ##  Paramters: none
    ##-----------------------------------------------------------------------
    def script_install(self):
        # Start config installation
        print("\n..Installation in progress")

        # Do this if "--config" was passed as an argument and serialized JSON was supplied
        if self.json_config != "":
            # Injected config (serialized JSON string object): test to make sure it's valid, then create JSON iFile with this data
            try:
                json_data = json.loads(self.json_config)

                # Parse the json config and fill in any missing values with defaults
                json_data = self.update_json(json_data)

                # Serialize JSON data
                json_config_final = json.dumps(json_data, indent = 4)

                # Get working directory
                this_work_directory = json_data["system"]["working_directory"]

                print("..Reading from serialized JSON config")

            except Exception as e:
                sys.stderr.write("ERROR: Imported JSON configuration is corrupt. Please fix the JSON and try import again. " + e.message + "\n")
                sys.stderr.flush()
                sys.exit(1)

        # Do this if "--configfile" was passed as an argument and a JSON file was supplied
        elif self.json_config_file != "":
            # Injected config (serialized JSON string object): test to make sure it's valid, then create JSON iFile with this data

            # Check if the file exists
            if not os.path.exists(self.json_config_file):
                print("Supplied file does not exist: " + self.json_config_file)

            # Check if file contents are valid JSON
            f = open(self.json_config_file, "r")
            f_content = f.read()
            f.close()
            try:
                json_data = json.loads(f_content)

                # Parse the json config and fill in any missing values with defaults
                json_data = self.update_json(json_data)

                # Serialize JSON data
                json_config_final = json.dumps(json_data, indent = 4)

                # Get working directory
                this_work_directory = json_data["system"]["working_directory"]

                print("..Reading from JSON config file")

            except Exception as e:
                sys.stderr.write("ERROR: Imported JSON configuration is corrupt. Please fix the JSON and try import again. " + e.message + "\n")
                sys.stderr.flush()
                sys.exit(1)

        # Do this if no --config/configfile argument was passed. Use the default JSON config.
        else:
            # No injected config: build JSON iFile with default values
            this_work_directory = "/shared/o365"

            # Dump JSON config to a temporary file
            json_data = copy.deepcopy(json_config_data)

            # Serialize JSON data
            json_config_final = json.dumps(json_data, indent = 4)

            print("..Reading from default JSON config")


        # Create the working directory if it doesn't already exit
        if not os.path.isdir(this_work_directory):
            os.mkdir(this_work_directory)
            print("..Working directory created: " + this_work_directory)

        # Copy script to the working directory
        #os.system('cp -f ' + os.path.basename(__file__) + ' ' + this_work_directory + '/sslo_o365_update.py')
        os.system('cp -f ' + os.path.abspath(__file__) + ' ' + this_work_directory + '/sslo_o365_update.py')
        print("..Script copied to working directory: " + this_work_directory + "/sslo_o365_update.py")

        # Write to a temporary file
        with open(this_work_directory + "/config.json", "w") as outfile:
            outfile.write(json_config_final)

        # Create the application service
        result = shell.getoutput("tmsh -a create sys application service o365_update traffic-group traffic-group-local-only device-group none")

        # Create the ifile configuration
        result = shell.getoutput("tmsh -a create sys file ifile o365_update.app/o365_config.json source-path file:" + this_work_directory + "/config.json")
        if "already exists" in result:
            # Overwrite existing content
            result = shell.getoutput("tmsh -a modify sys file ifile o365_update.app/o365_config.json source-path file:" + this_work_directory + "/config.json")
        os.remove(this_work_directory + "/config.json")
        print("..Configuration iFile created: o365_config.json")

        # Create cron.hourly config
        ## create cronstring
        run_date = json_data["schedule"]["run_date"]
        run_time = json_data["schedule"]["run_time"].split(":")

        if json_data["schedule"]["periods"] == "monthly":
            cronstring = str(run_time[1]) + " " + str(run_time[0]) + " " + str(run_date) + " * *"

        elif json_data["schedule"]["periods"] == "weekly":
            cronstring = str(run_time[1]) + " " + str(run_time[0]) + " * * " + str(run_date)

        elif json_data["schedule"]["periods"] == "daily":
            cronstring = str(run_time[1]) + " " + str(run_time[0]) + " * * *"

        ## search /etc/cron.d/0hourly for matching (existing) line and replace
        if json_data["schedule"]["periods"] != "none":
            ## Get current user first
            user = pwd.getpwuid( os.getuid() )[ 0 ]

            ## Clear out any existing script entry
            result = shell.getoutput("crontab -l | grep -v 'sslo_o365' | crontab")

            ## Write entry to bottom of the file
            shell.getoutput("echo \"" + cronstring + " python " + json_data["system"]["working_directory"] + "/sslo_o365_update.py" + "\" >> /var/spool/cron/" + user)

        else:
            ## if this an upgrade and schedule is none, make sure an entry does not exist in 0hourly
            result = shell.getoutput("crontab -l | grep -v 'sslo_o365' | crontab")


        print("[install-info] O365 URL updater configuration is saved successfully.")

        if self.force_update == True:
            print("\n[force-update]..Force update enabled - fetching Office365 URLs")
            self.update_o365()


    ##-----------------------------------------------------------------------
    ## Uninstall script function
    ##  Purpose: uninstall the script and configuration
    ##  Parameters:
    ##      Option      = none (normal uninstall), or full (full uninstall)
    ##-----------------------------------------------------------------------
    def script_uninstall(self, option):
        self.get_config()

        print("\n..Uninstall in progress")

        # Delete the configuration iFile
        result = shell.getoutput("tmsh -a delete sys file ifile o365_update.app/o365_config.json")
        print("..Configuration iFile deleted")
        # Get a list of all the file paths that ends with .txt from in specified directory
        fileList = os.listdir('/config/filestore/files_d/Common_d/ifile_d/')
        pattern = "*o365_config.json*"
        # Iterate over the list of filepaths & remove each file.
        for entry in fileList:
            if fnmatch.fnmatch(entry, pattern):
                try:
                    os.remove('/config/filestore/files_d/Common_d/ifile_d/' + entry)
                except:
                    print("Error while deleting file : ", filePath)
        # Delete working directory files
        try:
            os.remove(self.work_directory + "/guid.txt")
        except:
            pass

        try:
            os.remove(self.work_directory + "/o365_version.txt")
        except:
            pass
        print("..Configuration scratch files deleted")

        # Delete the cron config
        ## search /etc/cron.d/0hourly for matching (existing) line and replace
        result = shell.getoutput("crontab -l | grep -v 'sslo_o365' | crontab")


        if option == "none":
            print("[success-info] O365 URL updater configuration is deleted successfully.\n Note that this utility does not remove files from the working directory or any existing URL categories or data groups.\n\n")

        elif option == "full":
            # Use this option to completely remove all working directories, data groups, and URL categories

            # Delete ltm data group objects
            result = shell.getoutput("tmsh -a delete ltm data-group external o365_update.app/Office_365_Managed_All")
            result = shell.getoutput("tmsh -a delete ltm data-group external o365_update.app/Office_365_Managed_Allow")
            result = shell.getoutput("tmsh -a delete ltm data-group external o365_update.app/Office_365_Managed_IPv4")
            result = shell.getoutput("tmsh -a delete ltm data-group external o365_update.app/Office_365_Managed_IPv6")
            result = shell.getoutput("tmsh -a delete ltm data-group external o365_update.app/Office_365_Managed_Default")
            result = shell.getoutput("tmsh -a delete ltm data-group external o365_update.app/Office_365_Managed_Optimized")
            print("..LTM data-group objects deleted")

            # Delete sys data group objects
            result = shell.getoutput("tmsh -a delete sys file data-group o365_update.app/Office_365_Managed_All")
            result = shell.getoutput("tmsh -a delete sys file data-group o365_update.app/Office_365_Managed_Allow")
            result = shell.getoutput("tmsh -a delete sys file data-group o365_update.app/Office_365_Managed_Default")
            result = shell.getoutput("tmsh -a delete sys file data-group o365_update.app/Office_365_Managed_IPv4")
            result = shell.getoutput("tmsh -a delete sys file data-group o365_update.app/Office_365_Managed_IPv6")
            print("..System data-group objects deleted")

            # Delete URL categories
            result = shell.getoutput("tmsh -a delete sys url-db url-category o365_update.app/Office_365_All\(Managed\)")
            result = shell.getoutput("tmsh -a delete sys url-db url-category o365_update.app/Office_365_Allow\(Managed\)")
            result = shell.getoutput("tmsh -a delete sys url-db url-category o365_update.app/Office_365_Default\(Managed\)")
            result = shell.getoutput("tmsh -a delete sys url-db url-category o365_update.app/Office_365_Optimized\(Managed\)")
            print("..URL categories deleted")

            # Delete the application service
            result = shell.getoutput("tmsh -a delete sys application service o365_update.app/o365_update")
            print("..Application service deleted")
            print("If the Office365 configuration is deleted from the command line using the full_uninstall feature of the Python script and created again, the URL Category IDs will change. Therefore, if the SSL Orchestrator security policy uses any of these categories, the policy will need to be redeployed.")
            print("[success-info] ..Full uninstall complete. All unassigned data groups and URL categories have also been deleted.\n\n")


def main():
    # Instantial o365UrlManagement class
    o365 = o365UrlManagement()

    # -----------------------------------------------------------------------
    # Parse command line arguments (disable built-in help)
    # -----------------------------------------------------------------------
    parser = argparse.ArgumentParser(add_help=False)

    # Add --help option
    parser.add_argument("--help", action='store_const', const='none', help = "Show help.")
    parser.add_argument("--force", action='store_const', const='none', help = "Force an update.")

    # Add mutually-exclusive install/uninstall/force options
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--install", action='store_const', const='none', help = "Install the script.")
    group.add_argument("--uninstall", action='store_const', const='none', help = "Unintall the script.")
    group.add_argument("--full_uninstall", action='store_const', const='none', help = "Unintall the script. Remove everything.")
    #group.add_argument("--force", action='store_const', const='none', help = "Force an update.")
    group.add_argument("--printconfig", action='store_const', const='none', help = "Show the running configuration.")
    group.add_argument("--search", help = "Search the Office365 URL categories.")

    # Add mutually-exclusive config/configfile options
    group1 = parser.add_mutually_exclusive_group()
    group1.add_argument("--config", help = "Used with --install. Provide alternate JSON configuration information from a serialized JSON string object.")
    group1.add_argument("--configfile", help = "used with --install. Provide alternate JSON configuration information from a JSON file.")

    # Parse arguments
    args = parser.parse_args()

    # --help argument
    if args.help:
        o365.show_help()

    # --config argument and value
    if args.config:
        o365.json_config = str(args.config)

    # --configfile argument and value
    if args.configfile:
        o365.json_config_file = str(args.configfile)

    # --force argument
    if args.force:
        o365.force_update = True

    if args.search:
        o365.search(args.search)

    # --install/--uninstall arguments
    if args.install:
        o365.script_install()
    elif args.uninstall:
        o365.script_uninstall("none")
    elif args.full_uninstall:
        o365.script_uninstall('full')
    elif args.config:
        o365.show_help()
    elif args.printconfig:
        o365.print_config()
    elif args.search:
        o365.search()
    else:
        # No argument - run utility
        o365.update_o365()


if __name__ == '__main__':
    main()
