# SPDX-FileCopyrightText: © 2024 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Prints a space separalted list of GCC system include paths.
#
# For example:
#
#   gcc -v -xc -E /dev/null 2>&1 | awk -f includes.awk

/#include <...> search starts here:/ {
  inside_search_paths = 1; next
}

/End of search list./ {
  inside_search_paths = 0
}

inside_search_paths { print }
