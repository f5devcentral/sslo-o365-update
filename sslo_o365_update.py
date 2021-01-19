#!/bin/python
# -*- coding: utf-8 -*-
# O365 URL/IP update automation for BIG-IP
version = "7.1.3"
# Last Modified: January 2021
# Update author: Kevin Stewart, Sr. SSA F5 Networks
# Contributors: Regan Anderson, Brett Smith, F5 Networks
# Original author: Makoto Omura, F5 Networks Japan G.K.
#
# >>> NOTE: THIS VERSION OF THE OFFICE 365 SCRIPT IS SUPPORTED BY SSL ORCHESTRATOR 6.0 OR HIGHER <<<
#
# Updated for SSL Orchestrator by Kevin Stewart, SSA, F5 Networks
# Update 20210119 - added support for explicit proxy gateway (if required for Internet access)
# Update 20201104 - resolved URL category format issue
# Update 20201008 - to support additional enhancements by Kevin Stewart
#   - Updated to support HA mode (both peers perform updates and do not an trigger out-of-sync)
#   - Updated to resolve issue if multiple versions of configuration iFile exists (takes latest)
#   - Updated to include --force option to force a manual update (irrespective of config force_o365_record_refresh value)
# Update 20200925 - to support additional enhancements by Kevin Stewart
#   - Updated to support O365 optimize/allow/default categories as separate outputs
#   - Updated to support options to output to URL categories and/or URL data groups
#   - Updated to support included URLs
#   - Updated to support configuration stored in iFile
#   - Updated to include install|uninstall functions
# Update 20200207 - to support additional enhancements by Kevin Stewart
#   - Updated VERSION check routine to extract desired customer endpoint URI (previously was static "Worldwide")
#   - Updated to remove excluded_urls and excluded_ips
# Updated 20200130 - to support the following new functionality by Regan Anderson, F5 Networks
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
#   - Run the script with the --install option and a time interval (the time interval controls periodic updates, in seconds - 3600sec = 1hr).
#     python sslo_o365_update.py --install 3600
#
# To modify the configuration:
#   - tmsh edit the configuration json file
#     tmsh
#     edit sys file ifile o365_config.json
#
# To uninstall:
#   - Run the script with the --uninstall option. This will remove the iCall script and handler, and configuration json file.
#     python sslo_o365_update.py --uninstall
# 
# The installed script creates a working directory (/shared/o365), an configuration (iFile) json file, an iCall script, and iCall script periodic handler.
# The configuration json file controls the various settings of the script:
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
#         "ip4_datagroups": true|false    -> Create IPv4 data groups
#         "ip6_datagroups": true|false    -> Create IPv6 data groups
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
#     Provide URLs in list format - ex. ["m.facebook.com", ".itunes.apple.com", "bit.ly"]    
#     "included_urls": [] 
#   
#     Excluded IPs (IP must be exact match to IP as it exists in JSON record - IP/CIDR mask cannot be modified)
#     Provide IPs in list format - ex. ["191.234.140.0/22", "2620:1ec:a92::152/128"] 
#     "excluded_ips": [] 
#    
#     "system":
#         "force_refresh": true|false     -> Action if O365 endpoint list is not updated (a "fetch now" function)
#         "log_level": 1                  -> 0=none, 1=normal, 2=verbose
#         "proxy": "none" or "ip:port"    -> IP and port of an upstream explicit proxy listener (if required for Internet access), or "none".
#
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

import urllib2
import fnmatch
import uuid
import os
import re
import json
import commands
import datetime
import sys


#-----------------------------------------------------------------------
# System Options - Modify only when necessary
#-----------------------------------------------------------------------

# O365 custom URL category names
o365_category = "Office_365_Managed_All"
o365_category_optimized = "Office_365_Managed_Optimized"
o365_category_default = "Office_365_Managed_Default"
o365_category_allow = "Office_365_Managed_Allow"

# O365 data group names
dg_name_urls = "O365_URLs"
dg_name_ipv4 = "O365_IPv4"
dg_name_ipv6 = "O365_IPv6"
o365_dg = "Office_365_Managed_All"
o365_dg_optimize = "Office_365_Managed_Optimized"
o365_dg_default = "Office_365_Managed_Default"
o365_dg_allow = "Office_365_Managed_Allow"
o365_dg_ipv4 = "Office_365_Managed_IPv4"
o365_dg_ipv6 = "Office_365_Managed_IPv6"

# Microsoft Web Service URLs
url_ms_o365_endpoints = "endpoints.office.com"
url_ms_o365_version = "endpoints.office.com"
uri_ms_o365_version = "/version?ClientRequestId="

# Working directory, file name for guid & version management
work_directory = "/shared/o365/"
file_name_guid = "/shared/o365/guid.txt"
file_ms_o365_version = "/shared/o365/o365_version.txt"
log_dest_file = "/var/log/o365_update"


#-----------------------------------------------------------------------
# Implementation - Please do not modify
#-----------------------------------------------------------------------
list_urls_to_bypass = []
list_optimized_urls_to_bypass = []
list_default_urls_to_bypass = []
list_allow_urls_to_bypass = []
list_ipv4_to_pbr = []
list_ipv6_to_pbr = []
failover_state = ""

def log(lev, log_lev, msg):
    if int(log_lev) >= int(lev):
        log_string = "{0:%Y-%m-%d %H:%M:%S}".format(datetime.datetime.now()) + " " + msg + "\n"
        f = open(log_dest_file, "a")
        f.write(log_string)
        f.flush()
        f.close()
    return

def main():
    # Define global variables
    global customer_endpoint
    global service_areas_common
    global service_areas_exchange
    global service_areas_sharepoint
    global service_areas_skype
    global output_url_categories
    global output_url_datagroups
    global output_ip4_datagroups
    global output_ip6_datagroups
    global o365_categories_all
    global o365_categories_optimize
    global o365_categories_default
    global o365_categories_allow
    global only_required
    global excluded_urls
    global included_urls
    global excluded_ips
    global force_o365_record_refresh
    global log_level
    global proxy
    global force_update

    # Initialize force_update to false
    force_update = False

    # -----------------------------------------------------------------------
    # Parse command line arguments
    # -----------------------------------------------------------------------
    if not len(sys.argv) >= 2:
        print("\nError: No argument specified.\n\n")
        show_help()
    if sys.argv[1] == "-h":
        show_help()
    elif sys.argv[1] == "--install":
        script_install()
    elif sys.argv[1] == "--uninstall":
        script_uninstall()
    elif sys.argv[1] == "--force":
        force_update = True
        pass
    elif sys.argv[1] == "--go":
        pass
    else:
        print("\nError: Unrecognized argument\n\n")
        show_help()


    # -----------------------------------------------------------------------
    # Check if this script is installed by looking for iFile configuration, then load up configuration variables
    # -----------------------------------------------------------------------
    try:
        # Find all versions of the configuration iFile
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
            print("\nIt appears this script has not been installed yet. Aborting\n\nTo install this script, issue the command \"" + os.path.basename(__file__) + " --install <time>\"\n\n")
            show_help()
        
        try:
            f = open(o365_config, "r")
            f_content = f.read()
            f.close()
            config_data = json.loads(f_content)

            # read configuration parameters from the json config
            customer_endpoint           = config_data["endpoint"]
            service_area_common         = config_data["service_areas"]["common"]
            service_area_exchange       = config_data["service_areas"]["exchange"]
            service_area_sharepoint     = config_data["service_areas"]["sharepoint"]
            service_area_skype          = config_data["service_areas"]["skype"]
            output_url_categories       = config_data["outputs"]["url_categories"]
            output_url_datagroups       = config_data["outputs"]["url_datagroups"]
            output_ip4_datagroups       = config_data["outputs"]["ip4_datagroups"]
            output_ip6_datagroups       = config_data["outputs"]["ip6_datagroups"]
            o365_categories_all         = config_data["o365_categories"]["all"]
            o365_categories_optimize    = config_data["o365_categories"]["optimize"]
            o365_categories_default     = config_data["o365_categories"]["default"]
            o365_categories_allow       = config_data["o365_categories"]["allow"]
            only_required               = config_data["only_required"]
            excluded_urls               = config_data["excluded_urls"]
            included_urls               = config_data["included_urls"]
            excluded_ips                = config_data["excluded_ips"]
            force_o365_record_refresh   = config_data["system"]["force_refresh"]
            log_level                   = config_data["system"]["log_level"]
            proxy                       = config_data["system"]["proxy"]

        except:
            print("\nIt appears the JSON configuration file is either missing or corrupt. Run the script again with the --install <time> option to repair.")
            show_help()

    except:
        print("\nIt appears this script has not been installed yet. Aborting\n\nTo install this script, issue the command \"" + os.path.basename(__file__) + " --install <time>\"\n\n")
        show_help()
    

    # -----------------------------------------------------------------------
    # GUID management
    # -----------------------------------------------------------------------
    # Create the guid file if it doesn't exist
    if not os.path.isdir(work_directory):
        os.mkdir(work_directory)
        log(1, log_level, "Created work directory " + work_directory + " because it did not exist.")
    if not os.path.exists(file_name_guid):
        f = open(file_name_guid, "w")
        f.write("\n")
        f.flush()
        f.close()
        log(1, log_level, "Created GUID file " + file_name_guid + " because it did not exist.")

    # Read guid from file and validate.  Create one if not existent
    f = open(file_name_guid, "r")
    f_content = f.readline()
    f.close()
    if re.match('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', f_content):
        guid = f_content
        log(2, log_level, "Valid GUID is read from local file " + file_name_guid + ".")
    else:
        guid = str(uuid.uuid4())
        f = open(file_name_guid, "w")
        f.write(guid)
        f.flush()
        f.close()
        log(1, log_level, "Generated a new GUID, and saved it to " + file_name_guid + ".")


    # -----------------------------------------------------------------------
    # O365 endpoints list version check
    # -----------------------------------------------------------------------
    # Ensure that a local version exists
    if os.path.isfile(file_ms_o365_version):
        f = open(file_ms_o365_version, "r")
        f_content = f.readline()
        f.close()
        # Check if the VERSION record format is valid
        if re.match('[0-9]{10}', f_content):
            ms_o365_version_previous = f_content
            log(2, log_level, "Valid previous VERSION found in " + file_ms_o365_version + ".")
        else:
            ms_o365_version_previous = "1970010200"
            f = open(file_ms_o365_version, "w")
            f.write(ms_o365_version_previous)
            f.flush()
            f.close()
            log(1, log_level, "Valid previous VERSION was not found.  Wrote dummy value in " + file_ms_o365_version + ".")
    else:
        ms_o365_version_previous = "1970010200"
        f = open(file_ms_o365_version, "w")
        f.write(ms_o365_version_previous)
        f.flush()
        f.close()
        log(1, log_level, "Valid previous VERSION was not found.  Wrote dummy value in " + file_ms_o365_version + ".")


    # -----------------------------------------------------------------------
    # O365 endpoints list VERSION check
    # -----------------------------------------------------------------------
    # Read the version of previously received records. If different than stored information, then data is assumed new/changed
    request_string = uri_ms_o365_version + guid
    req_string = "https://" + url_ms_o365_version + request_string

    if proxy is not "none":
        proxyctl = urllib2.ProxyHandler({'https': proxy})
        opener = urllib2.build_opener(proxyctl)
        urllib2.install_opener(opener)
        res = urllib2.urlopen(req_string)
    else:
        res = urllib2.urlopen(req_string)

    if not res.getcode() == 200:
        # MS O365 version request failed - abort
        log(1, log_level, "VERSION request to MS web service failed.  Aborting operation.")
        sys.exit(0)
    else:
        # MS O365 version request succeeded
        log(2, log_level, "VERSION request to MS web service was successful.")
        dict_o365_version = json.loads(res.read())

    ms_o365_version_latest = ""
    for record in dict_o365_version:
        if record.has_key('instance'):
            if record["instance"] == customer_endpoint and record.has_key("latest"):
                latest = record["latest"]
                if re.match('[0-9]{10}', latest):
                    ms_o365_version_latest = latest
                    f = open(file_ms_o365_version, "w")
                    f.write(ms_o365_version_latest)
                    f.flush()
                    f.close()

    log(2, log_level, "Previous VERSION is " + ms_o365_version_previous)
    log(2, log_level, "Latest VERSION is " + ms_o365_version_latest)


    if force_update:
        log(1, log_level, "Command called with \"--force\" option. Manual update initiated.")
        pass
    elif ms_o365_version_latest == ms_o365_version_previous and force_o365_record_refresh == 0:
        log(1, log_level, "You already have the latest MS O365 URL/IP Address list: " + ms_o365_version_latest + ". Aborting operation.")
        sys.exit(0)


    # -----------------------------------------------------------------------
    # Request O365 endpoints list & put it in dictionaries
    # -----------------------------------------------------------------------
    # Make the request to fetch JSON data from Microsoft
    request_string = "/endpoints/" + customer_endpoint + "?ClientRequestId=" + guid    
    req_string = "https://" + url_ms_o365_endpoints + request_string

    if proxy is not "none":
        proxyctl = urllib2.ProxyHandler({'https': proxy})
        opener = urllib2.build_opener(proxyctl)
        urllib2.install_opener(opener)
        res = urllib2.urlopen(req_string)
    else:
        res = urllib2.urlopen(req_string)

    if not res.getcode() == 200:
        # MS O365 endpoints request failed - abort
        log(1, log_level, "ENDPOINTS request to MS web service failed. Aborting operation.")
        sys.exit(0)
    else:
        log(2, log_level, "ENDPOINTS request to MS web service was successful.")
        dict_o365_all = json.loads(res.read())

    # Process for each record(id) of the endpoint JSON data - this churns the JSON data into separate URL lists
    for dict_o365_record in dict_o365_all:
        service_area = str(dict_o365_record['serviceArea'])
        id = str(dict_o365_record['id'])

        if (only_required == 0) or (only_required and str(dict_o365_record['required']) == "True"):

            if (service_area_common and service_area == "Common") \
                or (service_area_exchange and service_area == "Exchange") \
                or (service_area_sharepoint and service_area == "SharePoint") \
                or (service_area_skype and service_area == "Skype"):

                if output_url_categories or output_url_datagroups:
                    # Append "urls" if existent in each record (full list)
                    if o365_categories_all and dict_o365_record.has_key('urls'):
                        list_urls = list(dict_o365_record['urls'])
                        for url in list_urls:
                            list_urls_to_bypass.append(url)
                        # append included_urls
                        for url in included_urls:
                            list_urls_to_bypass.append(url)

                    # Append "optimized" URLs if required (optimized list)
                    if o365_categories_optimize and dict_o365_record.has_key('urls') and dict_o365_record.has_key('category') and dict_o365_record['category'] == "Optimize":
                        list_optimized_urls = list(dict_o365_record['urls'])
                        for url in list_optimized_urls:
                            list_optimized_urls_to_bypass.append(url)

                    # Append "default" URLs if required (default list)
                    if o365_categories_default and dict_o365_record.has_key('urls')and dict_o365_record.has_key('category') and dict_o365_record['category'] == "Default":
                        list_default_urls = list(dict_o365_record['urls'])
                        for url in list_default_urls:
                            list_default_urls_to_bypass.append(url)

                    # Append "allow" URLs if required (allow list)
                    if o365_categories_allow and dict_o365_record.has_key('urls')and dict_o365_record.has_key('category') and dict_o365_record['category'] == "Allow":
                        list_allow_urls = list(dict_o365_record['urls'])
                        for url in list_allow_urls:
                            list_allow_urls_to_bypass.append(url)

                if output_ip4_datagroups or output_ip6_datagroups:
                    # Append "ips" if existent in each record
                    if dict_o365_record.has_key('ips'):
                        list_ips = list(dict_o365_record['ips'])
                        for ip in list_ips:
                            if re.match('^.+:', ip):
                                list_ipv6_to_pbr.append(ip)
                            else:
                                list_ipv4_to_pbr.append(ip)


    # -----------------------------------------------------------------------
    # (Re)process URLs/IPs to remove duplicates and excluded values
    # -----------------------------------------------------------------------
    if output_url_categories or output_url_datagroups:
        # Remove duplicate URLs in the list (full list) and remove set of excluded URLs from the list of collected URLs

        # full list
        if o365_categories_all:
            urls_undup = list(set(list_urls_to_bypass))
            for x_url in excluded_urls:
                urls_undup = [x for x in urls_undup if not x.endswith(x_url)]

        # optimized list 
        if o365_categories_optimize:
            urls_optimized_undup = list(set(list_optimized_urls_to_bypass))
            for x_url in excluded_urls:
                urls_optimized_undup = [x for x in urls_optimized_undup if not x.endswith(x_url)]

        # default list
        if o365_categories_default:
            urls_default_undup = list(set(list_default_urls_to_bypass))
            for x_url in excluded_urls:
                urls_default_undup = [x for x in urls_default_undup if not x.endswith(x_url)]

        # allow list
        if o365_categories_allow:
            urls_allow_undup = list(set(list_allow_urls_to_bypass))
            for x_url in excluded_urls:
                urls_allow_undup = [x for x in urls_allow_undup if not x.endswith(x_url)]


    if output_ip4_datagroups or output_ip6_datagroups:
        # Remove duplicate IPv4 addresses in the list
        ipv4_undup = list(set(list_ipv4_to_pbr))

        ## Remove set of excluded IPv4 addresses from the list of collected IPv4 addresses
        for x_ip in excluded_ips:
            ipv4_undup = [x for x in ipv4_undup if not x.endswith(x_ip)]

        # Remove duplicate IPv6 addresses in the list
        ipv6_undup = list(set(list_ipv6_to_pbr))

        ## Remove set of excluded IPv6 addresses from the list of collected IPv6 addresses
        for x_ip in excluded_ips:
            ipv6_undup = [x for x in ipv6_undup if not x.endswith(x_ip)]

    if not o365_categories_all:
        urls_undup = []
    if not output_ip4_datagroups:
        ipv4_undup = []
    if not output_ip6_datagroups:
        ipv6_undup = []
    log(1, log_level, "Number of unique ENDPOINTS to import : URL:" + str(len(urls_undup)) + ", IPv4 host/net:" + str(len(ipv4_undup)) + ", IPv6 host/net:" + str(len(ipv6_undup)))


    # -----------------------------------------------------------------------
    # O365 endpoint URLs re-formatted to fit into custom URL categories and/or data groups
    # -----------------------------------------------------------------------
    # This generates the temp files, data groups, and URL categories
    if output_url_categories or output_url_datagroups:

        if output_url_categories:
            if o365_categories_all:
                create_url_categories (o365_category, urls_undup, ms_o365_version_latest)

            if o365_categories_optimize:
                create_url_categories (o365_category_optimized, urls_optimized_undup, ms_o365_version_latest)

            if o365_categories_default:
                create_url_categories (o365_category_default, urls_default_undup, ms_o365_version_latest)

            if o365_categories_allow:
                create_url_categories (o365_category_allow, urls_allow_undup, ms_o365_version_latest)

        if output_url_datagroups:
            if o365_categories_all:
                create_url_datagroups (o365_dg, urls_undup)

            if o365_categories_optimize:
                create_url_datagroups (o365_dg_optimize, urls_optimized_undup)

            if o365_categories_default:
                create_url_datagroups (o365_dg_default, urls_default_undup)

            if o365_categories_allow:
                create_url_datagroups (o365_dg_allow, urls_allow_undup)

    if output_ip4_datagroups or output_ip6_datagroups:
        if output_ip4_datagroups:
            create_ip_datagroups (o365_dg_ipv4, ipv4_undup)

        if output_ip6_datagroups:
            create_ip_datagroups (o365_dg_ipv6, ipv6_undup)


    log(1, log_level, "Completed O365 URL/IP address update process.")


def create_url_categories (url_file, url_list, version_latest):
    # Initialize the url string
    str_urls_to_bypass = ""

    # Create new or clean out existing URL category - add the latest version as first entry
    result = commands.getoutput("tmsh list sys application service o365_update.app/o365_update")
    if "was not found" in result:
        result2 = commands.getoutput("tmsh create sys application service o365_update traffic-group traffic-group-local-only device-group none")
        log(2, log_level, "Application service not found. Creating o365_update.app/o365_update")
    
    result = commands.getoutput("tmsh list sys url-db url-category o365_update.app/" + url_file)
    if "was not found" in result:
        result2 = commands.getoutput("tmsh create /sys url-db url-category " + url_file + " display-name " + url_file + " app-service o365_update.app/o365_update urls replace-all-with { https://" + version_latest + "/ { type exact-match } } default-action allow")
        log(2, log_level, "O365 custom URL category (" + url_file + ") not found. Created new O365 custom category.")
    else:
        result2 = commands.getoutput("tmsh modify /sys url-db url-category " + url_file + " app-service o365_update.app/o365_update urls replace-all-with { https://" + version_latest + "/ { type exact-match } }")
        log(2, log_level, "O365 custom URL category (" + url_file + ") exists. Clearing entries for new data.")
    
    # Loop through URLs and insert into URL category    
    for url in url_list:
        # Force URL to lower case
        url = url.lower()

        # If URL starts with an asterisk, set as a glob-match URL, otherwise exact-match. Send to a string.
        if ('*' in url):
            # Escaping any asterisk characters
            url_processed = re.sub('\*', '\\*', url)
            str_urls_to_bypass = str_urls_to_bypass + " urls add { \"https://" + url_processed + "/\" { type glob-match } } urls add { \"http://" + url_processed + "/\" { type glob-match } }"
        else:
            str_urls_to_bypass = str_urls_to_bypass + " urls add { \"https://" + url + "/\" { type exact-match } } urls add { \"http://" + url + "/\" { type exact-match } }"

    # Import the URL entries
    result = commands.getoutput("tmsh modify /sys url-db url-category " + url_file + " app-service o365_update.app/o365_update" + str_urls_to_bypass)


def create_url_datagroups (url_file, url_list):
    # Write data to a file for import into data group
    fout = open(work_directory + url_file, 'w')
    for url in (list(sorted(set(url_list)))):
        # Replace any asterisk characters with a dot
        url_processed = re.sub('\*', '', url)
        fout.write("\"" + str(url_processed.lower()) + "\" := \"\",\n")
    fout.flush()
    fout.close()

    # Create URL data group files in TMSH if they don't already exist
    result = commands.getoutput("tmsh list sys application service o365_update.app/o365_update")
    if "was not found" in result:
        result2 = commands.getoutput("tmsh create sys application service o365_update traffic-group traffic-group-local-only device-group none")
        log(2, log_level, "Application service not found. Creating o365_update.app/o365_update")

    result = commands.getoutput("tmsh list /sys file data-group o365_update.app/" + url_file)
    if "was not found" in result:
        # Create (sys) external data group
        result2 = commands.getoutput("tmsh create /sys file data-group o365_update.app/" + url_file + " separator \":=\" source-path file:" + work_directory + url_file + " type string")
        # Create (ltm) link to external data group
        result3 = commands.getoutput("tmsh create /ltm data-group external o365_update.app/" + url_file + " external-file-name o365_update.app/" + url_file)
        log(2, log_level, "O365 URL data group (" + url_file + ") not found. Created new data group.")
    else:
        # Update (sys) external data group
        result2 = commands.getoutput("tmsh modify /sys file data-group o365_update.app/" + url_file + " source-path file:" + work_directory + url_file)
        # Update (ltm) link to external data group
        result3 = commands.getoutput("tmsh create /ltm data-group external o365_update.app/" + url_file + " external-file-name o365_update.app/" + url_file)
        log(2, log_level, "O365 URL data group (" + url_file + ") exists. Updated existing data group.")

    os.remove(work_directory + url_file)


def create_ip_datagroups (url_file, url_list):
    # Write data to a file for import into data group
    fout = open(work_directory + url_file, 'w')
    for ip in (list(sorted(url_list))):
        fout.write("network " + str(ip) + ",\n")
    fout.flush()
    fout.close()

    # Create URL data group files in TMSH if they don't already exist
    result = commands.getoutput("tmsh list sys application service o365_update.app/o365_update")
    if "was not found" in result:
        result2 = commands.getoutput("tmsh create sys application service o365_update traffic-group traffic-group-local-only device-group none")
        log(2, log_level, "Application service not found. Creating o365_update.app/o365_update")

    result = commands.getoutput("tmsh list /sys file data-group o365_update.app/" + url_file)
    if "was not found" in result:
        result2 = commands.getoutput("tmsh create /sys file data-group o365_update.app/" + url_file + " source-path file:" + work_directory + url_file + " type ip")
        result3 = commands.getoutput("tmsh create /ltm data-group external o365_update.app/" + url_file + " external-file-name o365_update.app/" + url_file)
        log(2, log_level, "O365 IPv4 data group (" + url_file + ") not found. Created new data group.")
    else:
        result2 = commands.getoutput("tmsh modify /sys file data-group o365_update.app/" + url_file + " source-path file:" + work_directory + url_file)
        result3 = commands.getoutput("tmsh create /ltm data-group external o365_update.app/" + url_file + " external-file-name o365_update.app/" + url_file)
        log(2, log_level, "O365 IPv4 data group (" + url_file + ") exists. Updated existing data group.")

    os.remove(work_directory + url_file)


def script_install ():
    if len(sys.argv) == 3:
        try:
            interval = int(sys.argv[2])
        except:
            print("\nError: Time parameter is not a valid integer")
            show_help()
    else:
        print("\nError: Time parameter is missing")
        show_help()

    print("\nInstallation in progress")
    # Create the working directory if it doesn't already exit
    if not os.path.isdir(work_directory):
        os.mkdir(work_directory)
        print("..Working directory created: " + work_directory)
    
    # Copy script to the working directory
    os.system('cp -f ' + os.path.basename(__file__) + ' ' + work_directory + 'sslo_o365_update.py')
    print("..Script copied to working directory: sslo_o365_update.py")

    # Dump JSON config to a temporary file
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
            "force_refresh": False,
            "log_level": 1,
            "proxy": "none"
        }
    }
    # Serialize JSON data
    json_config = json.dumps(json_config_data, indent = 4)
    
    # Write to a temporary file
    with open(work_directory + "config.json", "w") as outfile:
        outfile.write(json_config)

    # Create the ifile configuration
    result = commands.getoutput("tmsh create sys file ifile o365_config.json source-path file:" + work_directory + "config.json")
    if "already exists" in result:
        # Overwrite existing content
        result = commands.getoutput("tmsh modify sys file ifile o365_config.json source-path file:" + work_directory + "config.json")
    os.remove(work_directory + "config.json")
    print("..Configuration iFile created: o365_config.json")

    # Create the iCall script
    result = commands.getoutput("tmsh create sys icall script sslo_o365_update")
    result = commands.getoutput("tmsh modify sys icall script sslo_o365_update definition { catch { exec /bin/python " + work_directory + "sslo_o365_update.py --go } }")
    print("..iCall script created: sslo_o365_update")

    # Create the iCall periodic handler
    result = commands.getoutput("tmsh create sys icall handler periodic sslo_o365_update_handler script sslo_o365_update interval " + sys.argv[2])
    if "already exists" in result:
        # Overwrite existing content
        result = commands.getoutput("tmsh modify sys icall handler periodic sslo_o365_update_handler script sslo_o365_update interval " + sys.argv[2])
    print("..Periodic script handler created and set to " + sys.argv[2] + " seconds")

    print("..Installation complete")
    sys.exit(0)


def script_uninstall ():
    print("\nUninstall in progress - note that this utility will not remove files in the working directory, or any existing URL categories or data groups.")

    # Delete the iCall periodic handler
    result = commands.getoutput("tmsh delete sys icall handler periodic sslo_o365_update_handler")
    print("..Periodic script handler deleted")

    # Delete the iCall script
    result = commands.getoutput("tmsh delete sys icall script sslo_o365_update")
    print("..iCall script deleted")

    # Delete the configuration iFile
    result = commands.getoutput("tmsh delete sys file ifile o365_config.json")
    print("..Configuration iFile deleted")

    print("..Uninstall complete")
    sys.exit(0)


def show_help ():
    print("Office 365 URL Management Script. Version: " + version)
    print("\nCommand line options for this application are:\n")
    print("-h                   -> Show this help\n")
    print("--install <time>     -> Install the script and environment, and set script run time in seconds (ex. 3600 sec = 1 hr)\n")
    print("--uninstall          -> Uninstall the script and environment\n")
    print("--force              -> Force a manual update\n")
    print("--go                 -> Run this script\n\n")
    sys.exit(0)


if __name__=='__main__':
    main()
