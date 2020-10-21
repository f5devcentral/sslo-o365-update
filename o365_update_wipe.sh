#!/bin/bash

# Purpose: completely remove all remnants of the o365_update script. Note that this will fail if some objects are referenced elsewhere.
#
# Install:
# - copy to the BIG-IP
# - chmod +x o365_update_wipe.sh
# - ./o365_update_wipe.sh

python /shared/o365/sslo_o365_update.py --uninstall

rm -rf /shared/o365/

tmsh delete ltm data-group external o365_update.app/Office_365_Managed_All
tmsh delete ltm data-group external o365_update.app/Office_365_Managed_Allow
tmsh delete ltm data-group external o365_update.app/Office_365_Managed_IPv4
tmsh delete ltm data-group external o365_update.app/Office_365_Managed_IPv6
tmsh delete ltm data-group external o365_update.app/Office_365_Managed_Default
tmsh delete ltm data-group external o365_update.app/Office_365_Managed_Optimized

tmsh delete sys file data-group o365_update.app/Office_365_Managed_All
tmsh delete sys file data-group o365_update.app/Office_365_Managed_Allow
tmsh delete sys file data-group o365_update.app/Office_365_Managed_Default
tmsh delete sys file data-group o365_update.app/Office_365_Managed_IPv4
tmsh delete sys file data-group o365_update.app/Office_365_Managed_IPv6

tmsh delete sys url-db url-category o365_update.app/Office_365_Managed_All
tmsh delete sys url-db url-category o365_update.app/Office_365_Managed_Allow
tmsh delete sys url-db url-category o365_update.app/Office_365_Managed_Default
tmsh delete sys url-db url-category o365_update.app/Office_365_Managed_Optimized

tmsh delete sys application service o365_update.app/o365_update
