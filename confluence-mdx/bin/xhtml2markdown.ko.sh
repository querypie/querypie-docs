#!/usr/bin/env bash
# cd querypie-docs
# ./confluence-mdx/bin/generate_commands_for_xhtml2markdown.py confluence-mdx/var/list.en.txt

mkdir -p src/content/ko/.
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/608501837/page.xhtml src/content/ko/querypie-docs.mdx --public-dir=public --attachment-dir=/querypie-docs
echo 'Converted 608501837 to src/content/ko/querypie-docs.mdx'

mkdir -p src/content/ko/.
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544375335/page.xhtml src/content/ko/release-notes.mdx --public-dir=public --attachment-dir=/release-notes
echo 'Converted 544375335 to src/content/ko/release-notes.mdx'

mkdir -p src/content/ko/release-notes
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/1291878563/page.xhtml src/content/ko/release-notes/1120.mdx --public-dir=public --attachment-dir=/release-notes/1120
echo 'Converted 1291878563 to src/content/ko/release-notes/1120.mdx'

mkdir -p src/content/ko/release-notes
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/1171488777/page.xhtml src/content/ko/release-notes/1110-1112.mdx --public-dir=public --attachment-dir=/release-notes/1110-1112
echo 'Converted 1171488777 to src/content/ko/release-notes/1110-1112.mdx'

mkdir -p src/content/ko/release-notes
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/1064830173/page.xhtml src/content/ko/release-notes/1100.mdx --public-dir=public --attachment-dir=/release-notes/1100
echo 'Converted 1064830173 to src/content/ko/release-notes/1100.mdx'

mkdir -p src/content/ko/release-notes
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/954335909/page.xhtml src/content/ko/release-notes/1030-1034.mdx --public-dir=public --attachment-dir=/release-notes/1030-1034
echo 'Converted 954335909 to src/content/ko/release-notes/1030-1034.mdx'

mkdir -p src/content/ko/release-notes
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/703463517/page.xhtml src/content/ko/release-notes/1020-10212.mdx --public-dir=public --attachment-dir=/release-notes/1020-10212
echo 'Converted 703463517 to src/content/ko/release-notes/1020-10212.mdx'

mkdir -p src/content/ko/release-notes
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/604995641/page.xhtml src/content/ko/release-notes/1010-10111.mdx --public-dir=public --attachment-dir=/release-notes/1010-10111
echo 'Converted 604995641 to src/content/ko/release-notes/1010-10111.mdx'

mkdir -p src/content/ko/release-notes
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544375355/page.xhtml src/content/ko/release-notes/1000-1002.mdx --public-dir=public --attachment-dir=/release-notes/1000-1002
echo 'Converted 544375355 to src/content/ko/release-notes/1000-1002.mdx'

mkdir -p src/content/ko/release-notes
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544375370/page.xhtml src/content/ko/release-notes/9200-9202.mdx --public-dir=public --attachment-dir=/release-notes/9200-9202
echo 'Converted 544375370 to src/content/ko/release-notes/9200-9202.mdx'

mkdir -p src/content/ko/release-notes
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544375385/page.xhtml src/content/ko/release-notes/9190.mdx --public-dir=public --attachment-dir=/release-notes/9190
echo 'Converted 544375385 to src/content/ko/release-notes/9190.mdx'

mkdir -p src/content/ko/release-notes
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544375399/page.xhtml src/content/ko/release-notes/9180-9183.mdx --public-dir=public --attachment-dir=/release-notes/9180-9183
echo 'Converted 544375399 to src/content/ko/release-notes/9180-9183.mdx'

mkdir -p src/content/ko/release-notes
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544375414/page.xhtml src/content/ko/release-notes/9170-9171.mdx --public-dir=public --attachment-dir=/release-notes/9170-9171
echo 'Converted 544375414 to src/content/ko/release-notes/9170-9171.mdx'

mkdir -p src/content/ko/release-notes
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544375429/page.xhtml src/content/ko/release-notes/9160-9164.mdx --public-dir=public --attachment-dir=/release-notes/9160-9164
echo 'Converted 544375429 to src/content/ko/release-notes/9160-9164.mdx'

mkdir -p src/content/ko/release-notes
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544375443/page.xhtml src/content/ko/release-notes/9150-9154.mdx --public-dir=public --attachment-dir=/release-notes/9150-9154
echo 'Converted 544375443 to src/content/ko/release-notes/9150-9154.mdx'

mkdir -p src/content/ko/release-notes
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544375457/page.xhtml src/content/ko/release-notes/9140-9143.mdx --public-dir=public --attachment-dir=/release-notes/9140-9143
echo 'Converted 544375457 to src/content/ko/release-notes/9140-9143.mdx'

mkdir -p src/content/ko/release-notes
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544375471/page.xhtml src/content/ko/release-notes/9130-9135.mdx --public-dir=public --attachment-dir=/release-notes/9130-9135
echo 'Converted 544375471 to src/content/ko/release-notes/9130-9135.mdx'

mkdir -p src/content/ko/release-notes
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544375485/page.xhtml src/content/ko/release-notes/9120-91214.mdx --public-dir=public --attachment-dir=/release-notes/9120-91214
echo 'Converted 544375485 to src/content/ko/release-notes/9120-91214.mdx'

mkdir -p src/content/ko/release-notes/9120-91214
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544375505/page.xhtml src/content/ko/release-notes/9120-91214/menu-improvement-guide-9120.mdx --public-dir=public --attachment-dir=/release-notes/9120-91214/menu-improvement-guide-9120
echo 'Converted 544375505 to src/content/ko/release-notes/9120-91214/menu-improvement-guide-9120.mdx'

mkdir -p src/content/ko/release-notes
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544375587/page.xhtml src/content/ko/release-notes/9110-9115.mdx --public-dir=public --attachment-dir=/release-notes/9110-9115
echo 'Converted 544375587 to src/content/ko/release-notes/9110-9115.mdx'

mkdir -p src/content/ko/release-notes
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544375607/page.xhtml src/content/ko/release-notes/9100-9104.mdx --public-dir=public --attachment-dir=/release-notes/9100-9104
echo 'Converted 544375607 to src/content/ko/release-notes/9100-9104.mdx'

mkdir -p src/content/ko/release-notes/9100-9104
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544375624/page.xhtml src/content/ko/release-notes/9100-9104/external-api-changes-9100-version.mdx --public-dir=public --attachment-dir=/release-notes/9100-9104/external-api-changes-9100-version
echo 'Converted 544375624 to src/content/ko/release-notes/9100-9104/external-api-changes-9100-version.mdx'

mkdir -p src/content/ko/release-notes
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544375659/page.xhtml src/content/ko/release-notes/990-998.mdx --public-dir=public --attachment-dir=/release-notes/990-998
echo 'Converted 544375659 to src/content/ko/release-notes/990-998.mdx'

mkdir -p src/content/ko/release-notes/990-998
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544375685/page.xhtml src/content/ko/release-notes/990-998/external-api-changes-9810-version-994-version.mdx --public-dir=public --attachment-dir=/release-notes/990-998/external-api-changes-9810-version-994-version
echo 'Converted 544375685 to src/content/ko/release-notes/990-998/external-api-changes-9810-version-994-version.mdx'

mkdir -p src/content/ko/release-notes/990-998
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544375741/page.xhtml src/content/ko/release-notes/990-998/external-api-changes-994-version-995-version.mdx --public-dir=public --attachment-dir=/release-notes/990-998/external-api-changes-994-version-995-version
echo 'Converted 544375741 to src/content/ko/release-notes/990-998/external-api-changes-994-version-995-version.mdx'

mkdir -p src/content/ko/release-notes
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544375768/page.xhtml src/content/ko/release-notes/980-9812.mdx --public-dir=public --attachment-dir=/release-notes/980-9812
echo 'Converted 544375768 to src/content/ko/release-notes/980-9812.mdx'

mkdir -p src/content/ko/.
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544375784/page.xhtml src/content/ko/querypie-overview.mdx --public-dir=public --attachment-dir=/querypie-overview
echo 'Converted 544375784 to src/content/ko/querypie-overview.mdx'

mkdir -p src/content/ko/querypie-overview
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544112942/page.xhtml src/content/ko/querypie-overview/proxy-management.mdx --public-dir=public --attachment-dir=/querypie-overview/proxy-management
echo 'Converted 544112942 to src/content/ko/querypie-overview/proxy-management.mdx'

mkdir -p src/content/ko/querypie-overview/proxy-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544377869/page.xhtml src/content/ko/querypie-overview/proxy-management/enable-database-proxy.mdx --public-dir=public --attachment-dir=/querypie-overview/proxy-management/enable-database-proxy
echo 'Converted 544377869 to src/content/ko/querypie-overview/proxy-management/enable-database-proxy.mdx'

mkdir -p src/content/ko/querypie-overview
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544375859/page.xhtml src/content/ko/querypie-overview/system-architecture-overview.mdx --public-dir=public --attachment-dir=/querypie-overview/system-architecture-overview
echo 'Converted 544375859 to src/content/ko/querypie-overview/system-architecture-overview.mdx'

mkdir -p src/content/ko/querypie-overview
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544375808/page.xhtml src/content/ko/querypie-overview/installation-and-customer-support.mdx --public-dir=public --attachment-dir=/querypie-overview/installation-and-customer-support
echo 'Converted 544375808 to src/content/ko/querypie-overview/installation-and-customer-support.mdx'

mkdir -p src/content/ko/.
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544211126/page.xhtml src/content/ko/user-manual.mdx --public-dir=public --attachment-dir=/user-manual
echo 'Converted 544211126 to src/content/ko/user-manual.mdx'

mkdir -p src/content/ko/user-manual
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/578945174/page.xhtml src/content/ko/user-manual/my-dashboard.mdx --public-dir=public --attachment-dir=/user-manual/my-dashboard
echo 'Converted 578945174 to src/content/ko/user-manual/my-dashboard.mdx'

mkdir -p src/content/ko/user-manual/my-dashboard
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/793542657/page.xhtml src/content/ko/user-manual/my-dashboard/user-password-reset-via-email.mdx --public-dir=public --attachment-dir=/user-manual/my-dashboard/user-password-reset-via-email
echo 'Converted 793542657 to src/content/ko/user-manual/my-dashboard/user-password-reset-via-email.mdx'

mkdir -p src/content/ko/user-manual
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544377922/page.xhtml src/content/ko/user-manual/workflow.mdx --public-dir=public --attachment-dir=/user-manual/workflow
echo 'Converted 544377922 to src/content/ko/user-manual/workflow.mdx'

mkdir -p src/content/ko/user-manual/workflow
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544377968/page.xhtml src/content/ko/user-manual/workflow/requesting-db-access.mdx --public-dir=public --attachment-dir=/user-manual/workflow/requesting-db-access
echo 'Converted 544377968 to src/content/ko/user-manual/workflow/requesting-db-access.mdx'

mkdir -p src/content/ko/user-manual/workflow
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544378069/page.xhtml src/content/ko/user-manual/workflow/requesting-sql.mdx --public-dir=public --attachment-dir=/user-manual/workflow/requesting-sql
echo 'Converted 544378069 to src/content/ko/user-manual/workflow/requesting-sql.mdx'

mkdir -p src/content/ko/user-manual/workflow/requesting-sql
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/692355151/page.xhtml src/content/ko/user-manual/workflow/requesting-sql/using-execution-plan-explain-feature.mdx --public-dir=public --attachment-dir=/user-manual/workflow/requesting-sql/using-execution-plan-explain-feature
echo 'Converted 692355151 to src/content/ko/user-manual/workflow/requesting-sql/using-execution-plan-explain-feature.mdx'

mkdir -p src/content/ko/user-manual/workflow
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544378182/page.xhtml src/content/ko/user-manual/workflow/requesting-sql-export.mdx --public-dir=public --attachment-dir=/user-manual/workflow/requesting-sql-export
echo 'Converted 544378182 to src/content/ko/user-manual/workflow/requesting-sql-export.mdx'

mkdir -p src/content/ko/user-manual/workflow
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/712769539/page.xhtml src/content/ko/user-manual/workflow/requesting-unmasking-mask-removal-request.mdx --public-dir=public --attachment-dir=/user-manual/workflow/requesting-unmasking-mask-removal-request
echo 'Converted 712769539 to src/content/ko/user-manual/workflow/requesting-unmasking-mask-removal-request.mdx'

mkdir -p src/content/ko/user-manual/workflow
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/1060306945/page.xhtml src/content/ko/user-manual/workflow/requesting-restricted-data-access.mdx --public-dir=public --attachment-dir=/user-manual/workflow/requesting-restricted-data-access
echo 'Converted 1060306945 to src/content/ko/user-manual/workflow/requesting-restricted-data-access.mdx'

mkdir -p src/content/ko/user-manual/workflow
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544378254/page.xhtml src/content/ko/user-manual/workflow/requesting-server-access.mdx --public-dir=public --attachment-dir=/user-manual/workflow/requesting-server-access
echo 'Converted 544378254 to src/content/ko/user-manual/workflow/requesting-server-access.mdx'

mkdir -p src/content/ko/user-manual/workflow
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/878936417/page.xhtml src/content/ko/user-manual/workflow/requesting-server-privilege.mdx --public-dir=public --attachment-dir=/user-manual/workflow/requesting-server-privilege
echo 'Converted 878936417 to src/content/ko/user-manual/workflow/requesting-server-privilege.mdx'

mkdir -p src/content/ko/user-manual/workflow
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544378348/page.xhtml src/content/ko/user-manual/workflow/requesting-access-role.mdx --public-dir=public --attachment-dir=/user-manual/workflow/requesting-access-role
echo 'Converted 544378348 to src/content/ko/user-manual/workflow/requesting-access-role.mdx'

mkdir -p src/content/ko/user-manual/workflow
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/1055358996/page.xhtml src/content/ko/user-manual/workflow/requesting-ip-registration.mdx --public-dir=public --attachment-dir=/user-manual/workflow/requesting-ip-registration
echo 'Converted 1055358996 to src/content/ko/user-manual/workflow/requesting-ip-registration.mdx'

mkdir -p src/content/ko/user-manual/workflow
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/568918170/page.xhtml src/content/ko/user-manual/workflow/approval-additional-features-proxy-approval-resubmission-etc.mdx --public-dir=public --attachment-dir=/user-manual/workflow/approval-additional-features-proxy-approval-resubmission-etc
echo 'Converted 568918170 to src/content/ko/user-manual/workflow/approval-additional-features-proxy-approval-resubmission-etc.mdx'

mkdir -p src/content/ko/user-manual/workflow
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/1070006273/page.xhtml src/content/ko/user-manual/workflow/requesting-db-policy-exception.mdx --public-dir=public --attachment-dir=/user-manual/workflow/requesting-db-policy-exception
echo 'Converted 1070006273 to src/content/ko/user-manual/workflow/requesting-db-policy-exception.mdx'

mkdir -p src/content/ko/user-manual
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544380204/page.xhtml src/content/ko/user-manual/database-access-control.mdx --public-dir=public --attachment-dir=/user-manual/database-access-control
echo 'Converted 544380204 to src/content/ko/user-manual/database-access-control.mdx'

mkdir -p src/content/ko/user-manual/database-access-control
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544380222/page.xhtml src/content/ko/user-manual/database-access-control/connecting-with-web-sql-editor.mdx --public-dir=public --attachment-dir=/user-manual/database-access-control/connecting-with-web-sql-editor
echo 'Converted 544380222 to src/content/ko/user-manual/database-access-control/connecting-with-web-sql-editor.mdx'

mkdir -p src/content/ko/user-manual/database-access-control
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544380354/page.xhtml src/content/ko/user-manual/database-access-control/setting-default-privilege.mdx --public-dir=public --attachment-dir=/user-manual/database-access-control/setting-default-privilege
echo 'Converted 544380354 to src/content/ko/user-manual/database-access-control/setting-default-privilege.mdx'

mkdir -p src/content/ko/user-manual/database-access-control
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/559906893/page.xhtml src/content/ko/user-manual/database-access-control/connecting-to-proxy-without-agent.mdx --public-dir=public --attachment-dir=/user-manual/database-access-control/connecting-to-proxy-without-agent
echo 'Converted 559906893 to src/content/ko/user-manual/database-access-control/connecting-to-proxy-without-agent.mdx'

mkdir -p src/content/ko/user-manual/database-access-control
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/820609510/page.xhtml src/content/ko/user-manual/database-access-control/connecting-via-google-bigquery-oauth-authentication.mdx --public-dir=public --attachment-dir=/user-manual/database-access-control/connecting-via-google-bigquery-oauth-authentication
echo 'Converted 820609510 to src/content/ko/user-manual/database-access-control/connecting-via-google-bigquery-oauth-authentication.mdx'

mkdir -p src/content/ko/user-manual/database-access-control
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/880181257/page.xhtml src/content/ko/user-manual/database-access-control/connecting-to-custom-data-source.mdx --public-dir=public --attachment-dir=/user-manual/database-access-control/connecting-to-custom-data-source
echo 'Converted 880181257 to src/content/ko/user-manual/database-access-control/connecting-to-custom-data-source.mdx'

mkdir -p src/content/ko/user-manual
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544381369/page.xhtml src/content/ko/user-manual/server-access-control.mdx --public-dir=public --attachment-dir=/user-manual/server-access-control
echo 'Converted 544381369 to src/content/ko/user-manual/server-access-control.mdx'

mkdir -p src/content/ko/user-manual/server-access-control
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544381383/page.xhtml src/content/ko/user-manual/server-access-control/connecting-to-authorized-servers.mdx --public-dir=public --attachment-dir=/user-manual/server-access-control/connecting-to-authorized-servers
echo 'Converted 544381383 to src/content/ko/user-manual/server-access-control/connecting-to-authorized-servers.mdx'

mkdir -p src/content/ko/user-manual/server-access-control
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544381410/page.xhtml src/content/ko/user-manual/server-access-control/using-web-terminal.mdx --public-dir=public --attachment-dir=/user-manual/server-access-control/using-web-terminal
echo 'Converted 544381410 to src/content/ko/user-manual/server-access-control/using-web-terminal.mdx'

mkdir -p src/content/ko/user-manual/server-access-control
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544381477/page.xhtml src/content/ko/user-manual/server-access-control/using-web-sftp.mdx --public-dir=public --attachment-dir=/user-manual/server-access-control/using-web-sftp
echo 'Converted 544381477 to src/content/ko/user-manual/server-access-control/using-web-sftp.mdx'

mkdir -p src/content/ko/user-manual
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544384011/page.xhtml src/content/ko/user-manual/kubernetes-access-control.mdx --public-dir=public --attachment-dir=/user-manual/kubernetes-access-control
echo 'Converted 544384011 to src/content/ko/user-manual/kubernetes-access-control.mdx'

mkdir -p src/content/ko/user-manual/kubernetes-access-control
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544384025/page.xhtml src/content/ko/user-manual/kubernetes-access-control/checking-access-permission-list.mdx --public-dir=public --attachment-dir=/user-manual/kubernetes-access-control/checking-access-permission-list
echo 'Converted 544384025 to src/content/ko/user-manual/kubernetes-access-control/checking-access-permission-list.mdx'

mkdir -p src/content/ko/user-manual
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/1064829218/page.xhtml src/content/ko/user-manual/web-access-control.mdx --public-dir=public --attachment-dir=/user-manual/web-access-control
echo 'Converted 1064829218 to src/content/ko/user-manual/web-access-control.mdx'

mkdir -p src/content/ko/user-manual/web-access-control
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/1073709107/page.xhtml src/content/ko/user-manual/web-access-control/installing-root-ca-certificate-and-extension.mdx --public-dir=public --attachment-dir=/user-manual/web-access-control/installing-root-ca-certificate-and-extension
echo 'Converted 1073709107 to src/content/ko/user-manual/web-access-control/installing-root-ca-certificate-and-extension.mdx'

mkdir -p src/content/ko/user-manual/web-access-control
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/1064796396/page.xhtml src/content/ko/user-manual/web-access-control/accessing-web-applications-websites.mdx --public-dir=public --attachment-dir=/user-manual/web-access-control/accessing-web-applications-websites
echo 'Converted 1064796396 to src/content/ko/user-manual/web-access-control/accessing-web-applications-websites.mdx'

mkdir -p src/content/ko/user-manual
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/568950885/page.xhtml src/content/ko/user-manual/preferences.mdx --public-dir=public --attachment-dir=/user-manual/preferences
echo 'Converted 568950885 to src/content/ko/user-manual/preferences.mdx'

mkdir -p src/content/ko/user-manual
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544112828/page.xhtml src/content/ko/user-manual/user-agent.mdx --public-dir=public --attachment-dir=/user-manual/user-agent
echo 'Converted 544112828 to src/content/ko/user-manual/user-agent.mdx'

mkdir -p src/content/ko/user-manual
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/852066413/page.xhtml src/content/ko/user-manual/multi-agent.mdx --public-dir=public --attachment-dir=/user-manual/multi-agent
echo 'Converted 852066413 to src/content/ko/user-manual/multi-agent.mdx'

mkdir -p src/content/ko/user-manual/multi-agent
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/912425276/page.xhtml src/content/ko/user-manual/multi-agent/multi-agent-linux-installation-and-usage-guide.mdx --public-dir=public --attachment-dir=/user-manual/multi-agent/multi-agent-linux-installation-and-usage-guide
echo 'Converted 912425276 to src/content/ko/user-manual/multi-agent/multi-agent-linux-installation-and-usage-guide.mdx'

mkdir -p src/content/ko/user-manual/multi-agent
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/912425288/page.xhtml src/content/ko/user-manual/multi-agent/multi-agent-seamless-ssh-usage-guide.mdx --public-dir=public --attachment-dir=/user-manual/multi-agent/multi-agent-seamless-ssh-usage-guide
echo 'Converted 912425288 to src/content/ko/user-manual/multi-agent/multi-agent-seamless-ssh-usage-guide.mdx'

mkdir -p src/content/ko/user-manual/multi-agent
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/919240916/page.xhtml src/content/ko/user-manual/multi-agent/multi-agent-3rd-party-tool-support-list-by-os.mdx --public-dir=public --attachment-dir=/user-manual/multi-agent/multi-agent-3rd-party-tool-support-list-by-os
echo 'Converted 919240916 to src/content/ko/user-manual/multi-agent/multi-agent-3rd-party-tool-support-list-by-os.mdx'

mkdir -p src/content/ko/.
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544178405/page.xhtml src/content/ko/administrator-manual.mdx --public-dir=public --attachment-dir=/administrator-manual
echo 'Converted 544178405 to src/content/ko/administrator-manual.mdx'

mkdir -p src/content/ko/administrator-manual
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544080057/page.xhtml src/content/ko/administrator-manual/general.mdx --public-dir=public --attachment-dir=/administrator-manual/general
echo 'Converted 544080057 to src/content/ko/administrator-manual/general.mdx'

mkdir -p src/content/ko/administrator-manual/general
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/543948978/page.xhtml src/content/ko/administrator-manual/general/company-management.mdx --public-dir=public --attachment-dir=/administrator-manual/general/company-management
echo 'Converted 543948978 to src/content/ko/administrator-manual/general/company-management.mdx'

mkdir -p src/content/ko/administrator-manual/general/company-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544145591/page.xhtml src/content/ko/administrator-manual/general/company-management/general.mdx --public-dir=public --attachment-dir=/administrator-manual/general/company-management/general
echo 'Converted 544145591 to src/content/ko/administrator-manual/general/company-management/general.mdx'

mkdir -p src/content/ko/administrator-manual/general/company-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544178422/page.xhtml src/content/ko/administrator-manual/general/company-management/security.mdx --public-dir=public --attachment-dir=/administrator-manual/general/company-management/security
echo 'Converted 544178422 to src/content/ko/administrator-manual/general/company-management/security.mdx'

mkdir -p src/content/ko/administrator-manual/general/company-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544112846/page.xhtml src/content/ko/administrator-manual/general/company-management/allowed-zones.mdx --public-dir=public --attachment-dir=/administrator-manual/general/company-management/allowed-zones
echo 'Converted 544112846 to src/content/ko/administrator-manual/general/company-management/allowed-zones.mdx'

mkdir -p src/content/ko/administrator-manual/general/company-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544243925/page.xhtml src/content/ko/administrator-manual/general/company-management/channels.mdx --public-dir=public --attachment-dir=/administrator-manual/general/company-management/channels
echo 'Converted 544243925 to src/content/ko/administrator-manual/general/company-management/channels.mdx'

mkdir -p src/content/ko/administrator-manual/general/company-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/543981760/page.xhtml src/content/ko/administrator-manual/general/company-management/alerts.mdx --public-dir=public --attachment-dir=/administrator-manual/general/company-management/alerts
echo 'Converted 543981760 to src/content/ko/administrator-manual/general/company-management/alerts.mdx'

mkdir -p src/content/ko/administrator-manual/general/company-management/alerts
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/793608206/page.xhtml src/content/ko/administrator-manual/general/company-management/alerts/new-request-template-variables-by-request-type.mdx --public-dir=public --attachment-dir=/administrator-manual/general/company-management/alerts/new-request-template-variables-by-request-type
echo 'Converted 793608206 to src/content/ko/administrator-manual/general/company-management/alerts/new-request-template-variables-by-request-type.mdx'

mkdir -p src/content/ko/administrator-manual/general/company-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544178443/page.xhtml src/content/ko/administrator-manual/general/company-management/licenses.mdx --public-dir=public --attachment-dir=/administrator-manual/general/company-management/licenses
echo 'Converted 544178443 to src/content/ko/administrator-manual/general/company-management/licenses.mdx'

mkdir -p src/content/ko/administrator-manual/general
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544375969/page.xhtml src/content/ko/administrator-manual/general/user-management.mdx --public-dir=public --attachment-dir=/administrator-manual/general/user-management
echo 'Converted 544375969 to src/content/ko/administrator-manual/general/user-management.mdx'

mkdir -p src/content/ko/administrator-manual/general/user-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544047331/page.xhtml src/content/ko/administrator-manual/general/user-management/users.mdx --public-dir=public --attachment-dir=/administrator-manual/general/user-management/users
echo 'Converted 544047331 to src/content/ko/administrator-manual/general/user-management/users.mdx'

mkdir -p src/content/ko/administrator-manual/general/user-management/users
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544376787/page.xhtml src/content/ko/administrator-manual/general/user-management/users/user-profile.mdx --public-dir=public --attachment-dir=/administrator-manual/general/user-management/users/user-profile
echo 'Converted 544376787 to src/content/ko/administrator-manual/general/user-management/users/user-profile.mdx'

mkdir -p src/content/ko/administrator-manual/general/user-management/users
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/920944732/page.xhtml src/content/ko/administrator-manual/general/user-management/users/password-change-enforcement-and-account-deletion-feature-for-qp-admin-default-account.mdx --public-dir=public --attachment-dir=/administrator-manual/general/user-management/users/password-change-enforcement-and-account-deletion-feature-for-qp-admin-default-account
echo 'Converted 920944732 to src/content/ko/administrator-manual/general/user-management/users/password-change-enforcement-and-account-deletion-feature-for-qp-admin-default-account.mdx'

mkdir -p src/content/ko/administrator-manual/general/user-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544047341/page.xhtml src/content/ko/administrator-manual/general/user-management/groups.mdx --public-dir=public --attachment-dir=/administrator-manual/general/user-management/groups
echo 'Converted 544047341 to src/content/ko/administrator-manual/general/user-management/groups.mdx'

mkdir -p src/content/ko/administrator-manual/general/user-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/543948996/page.xhtml src/content/ko/administrator-manual/general/user-management/roles.mdx --public-dir=public --attachment-dir=/administrator-manual/general/user-management/roles
echo 'Converted 543948996 to src/content/ko/administrator-manual/general/user-management/roles.mdx'

mkdir -p src/content/ko/administrator-manual/general/user-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544376982/page.xhtml src/content/ko/administrator-manual/general/user-management/profile-editor.mdx --public-dir=public --attachment-dir=/administrator-manual/general/user-management/profile-editor
echo 'Converted 544376982 to src/content/ko/administrator-manual/general/user-management/profile-editor.mdx'

mkdir -p src/content/ko/administrator-manual/general/user-management/profile-editor
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/953221256/page.xhtml src/content/ko/administrator-manual/general/user-management/profile-editor/custom-attribute.mdx --public-dir=public --attachment-dir=/administrator-manual/general/user-management/profile-editor/custom-attribute
echo 'Converted 953221256 to src/content/ko/administrator-manual/general/user-management/profile-editor/custom-attribute.mdx'

mkdir -p src/content/ko/administrator-manual/general/user-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544375984/page.xhtml src/content/ko/administrator-manual/general/user-management/authentication.mdx --public-dir=public --attachment-dir=/administrator-manual/general/user-management/authentication
echo 'Converted 544375984 to src/content/ko/administrator-manual/general/user-management/authentication.mdx'

mkdir -p src/content/ko/administrator-manual/general/user-management/authentication
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544376004/page.xhtml src/content/ko/administrator-manual/general/user-management/authentication/integrating-with-ldap.mdx --public-dir=public --attachment-dir=/administrator-manual/general/user-management/authentication/integrating-with-ldap
echo 'Converted 544376004 to src/content/ko/administrator-manual/general/user-management/authentication/integrating-with-ldap.mdx'

mkdir -p src/content/ko/administrator-manual/general/user-management/authentication
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544376100/page.xhtml src/content/ko/administrator-manual/general/user-management/authentication/integrating-with-okta.mdx --public-dir=public --attachment-dir=/administrator-manual/general/user-management/authentication/integrating-with-okta
echo 'Converted 544376100 to src/content/ko/administrator-manual/general/user-management/authentication/integrating-with-okta.mdx'

mkdir -p src/content/ko/administrator-manual/general/user-management/authentication
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544376183/page.xhtml src/content/ko/administrator-manual/general/user-management/authentication/integrating-with-aws-sso.mdx --public-dir=public --attachment-dir=/administrator-manual/general/user-management/authentication/integrating-with-aws-sso
echo 'Converted 544376183 to src/content/ko/administrator-manual/general/user-management/authentication/integrating-with-aws-sso.mdx'

mkdir -p src/content/ko/administrator-manual/general/user-management/authentication
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/619381289/page.xhtml src/content/ko/administrator-manual/general/user-management/authentication/integrating-with-google-saml.mdx --public-dir=public --attachment-dir=/administrator-manual/general/user-management/authentication/integrating-with-google-saml
echo 'Converted 619381289 to src/content/ko/administrator-manual/general/user-management/authentication/integrating-with-google-saml.mdx'

mkdir -p src/content/ko/administrator-manual/general/user-management/authentication
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/793575425/page.xhtml src/content/ko/administrator-manual/general/user-management/authentication/setting-up-multi-factor-authentication.mdx --public-dir=public --attachment-dir=/administrator-manual/general/user-management/authentication/setting-up-multi-factor-authentication
echo 'Converted 793575425 to src/content/ko/administrator-manual/general/user-management/authentication/setting-up-multi-factor-authentication.mdx'

mkdir -p src/content/ko/administrator-manual/general/user-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544376236/page.xhtml src/content/ko/administrator-manual/general/user-management/provisioning.mdx --public-dir=public --attachment-dir=/administrator-manual/general/user-management/provisioning
echo 'Converted 544376236 to src/content/ko/administrator-manual/general/user-management/provisioning.mdx'

mkdir -p src/content/ko/administrator-manual/general/user-management/provisioning
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544376265/page.xhtml src/content/ko/administrator-manual/general/user-management/provisioning/activating-provisioning.mdx --public-dir=public --attachment-dir=/administrator-manual/general/user-management/provisioning/activating-provisioning
echo 'Converted 544376265 to src/content/ko/administrator-manual/general/user-management/provisioning/activating-provisioning.mdx'

mkdir -p src/content/ko/administrator-manual/general/user-management/provisioning
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544376394/page.xhtml src/content/ko/administrator-manual/general/user-management/provisioning/okta-provisioning-integration-guide.mdx --public-dir=public --attachment-dir=/administrator-manual/general/user-management/provisioning/okta-provisioning-integration-guide
echo 'Converted 544376394 to src/content/ko/administrator-manual/general/user-management/provisioning/okta-provisioning-integration-guide.mdx'

mkdir -p src/content/ko/administrator-manual/general
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544178462/page.xhtml src/content/ko/administrator-manual/general/workflow-management.mdx --public-dir=public --attachment-dir=/administrator-manual/general/workflow-management
echo 'Converted 544178462 to src/content/ko/administrator-manual/general/workflow-management.mdx'

mkdir -p src/content/ko/administrator-manual/general/workflow-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544047359/page.xhtml src/content/ko/administrator-manual/general/workflow-management/all-requests.mdx --public-dir=public --attachment-dir=/administrator-manual/general/workflow-management/all-requests
echo 'Converted 544047359 to src/content/ko/administrator-manual/general/workflow-management/all-requests.mdx'

mkdir -p src/content/ko/administrator-manual/general/workflow-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544378513/page.xhtml src/content/ko/administrator-manual/general/workflow-management/approval-rules.mdx --public-dir=public --attachment-dir=/administrator-manual/general/workflow-management/approval-rules
echo 'Converted 544378513 to src/content/ko/administrator-manual/general/workflow-management/approval-rules.mdx'

mkdir -p src/content/ko/administrator-manual/general/workflow-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/561414376/page.xhtml src/content/ko/administrator-manual/general/workflow-management/workflow-configurations.mdx --public-dir=public --attachment-dir=/administrator-manual/general/workflow-management/workflow-configurations
echo 'Converted 561414376 to src/content/ko/administrator-manual/general/workflow-management/workflow-configurations.mdx'

mkdir -p src/content/ko/administrator-manual/general
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544112865/page.xhtml src/content/ko/administrator-manual/general/system.mdx --public-dir=public --attachment-dir=/administrator-manual/general/system
echo 'Converted 544112865 to src/content/ko/administrator-manual/general/system.mdx'

mkdir -p src/content/ko/administrator-manual/general/system
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544080097/page.xhtml src/content/ko/administrator-manual/general/system/integrations.mdx --public-dir=public --attachment-dir=/administrator-manual/general/system/integrations
echo 'Converted 544080097 to src/content/ko/administrator-manual/general/system/integrations.mdx'

mkdir -p src/content/ko/administrator-manual/general/system/integrations
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544379393/page.xhtml src/content/ko/administrator-manual/general/system/integrations/integrating-with-syslog.mdx --public-dir=public --attachment-dir=/administrator-manual/general/system/integrations/integrating-with-syslog
echo 'Converted 544379393 to src/content/ko/administrator-manual/general/system/integrations/integrating-with-syslog.mdx'

mkdir -p src/content/ko/administrator-manual/general/system/integrations
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/557940795/page.xhtml src/content/ko/administrator-manual/general/system/integrations/integrating-with-splunk.mdx --public-dir=public --attachment-dir=/administrator-manual/general/system/integrations/integrating-with-splunk
echo 'Converted 557940795 to src/content/ko/administrator-manual/general/system/integrations/integrating-with-splunk.mdx'

mkdir -p src/content/ko/administrator-manual/general/system/integrations
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544379587/page.xhtml src/content/ko/administrator-manual/general/system/integrations/integrating-with-secret-store.mdx --public-dir=public --attachment-dir=/administrator-manual/general/system/integrations/integrating-with-secret-store
echo 'Converted 544379587 to src/content/ko/administrator-manual/general/system/integrations/integrating-with-secret-store.mdx'

mkdir -p src/content/ko/administrator-manual/general/system/integrations
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/798064641/page.xhtml src/content/ko/administrator-manual/general/system/integrations/integrating-with-email.mdx --public-dir=public --attachment-dir=/administrator-manual/general/system/integrations/integrating-with-email
echo 'Converted 798064641 to src/content/ko/administrator-manual/general/system/integrations/integrating-with-email.mdx'

mkdir -p src/content/ko/administrator-manual/general/system/integrations
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/1267007528/page.xhtml src/content/ko/administrator-manual/general/system/integrations/integrating-with-event-callback.mdx --public-dir=public --attachment-dir=/administrator-manual/general/system/integrations/integrating-with-event-callback
echo 'Converted 1267007528 to src/content/ko/administrator-manual/general/system/integrations/integrating-with-event-callback.mdx'

mkdir -p src/content/ko/administrator-manual/general/system/integrations
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/811401365/page.xhtml src/content/ko/administrator-manual/general/system/integrations/integrating-google-cloud-api-for-oauth-20.mdx --public-dir=public --attachment-dir=/administrator-manual/general/system/integrations/integrating-google-cloud-api-for-oauth-20
echo 'Converted 811401365 to src/content/ko/administrator-manual/general/system/integrations/integrating-google-cloud-api-for-oauth-20.mdx'

mkdir -p src/content/ko/administrator-manual/general/system/integrations
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/883654669/page.xhtml src/content/ko/administrator-manual/general/system/integrations/integrating-with-slack-dm.mdx --public-dir=public --attachment-dir=/administrator-manual/general/system/integrations/integrating-with-slack-dm
echo 'Converted 883654669 to src/content/ko/administrator-manual/general/system/integrations/integrating-with-slack-dm.mdx'

mkdir -p src/content/ko/administrator-manual/general/system/integrations/integrating-with-slack-dm
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544378759/page.xhtml src/content/ko/administrator-manual/general/system/integrations/integrating-with-slack-dm/slack-dm-workflow-notification-types.mdx --public-dir=public --attachment-dir=/administrator-manual/general/system/integrations/integrating-with-slack-dm/slack-dm-workflow-notification-types
echo 'Converted 544378759 to src/content/ko/administrator-manual/general/system/integrations/integrating-with-slack-dm/slack-dm-workflow-notification-types.mdx'

mkdir -p src/content/ko/administrator-manual/general/system
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544377652/page.xhtml src/content/ko/administrator-manual/general/system/api-token.mdx --public-dir=public --attachment-dir=/administrator-manual/general/system/api-token
echo 'Converted 544377652 to src/content/ko/administrator-manual/general/system/api-token.mdx'

mkdir -p src/content/ko/administrator-manual/general/system
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544211220/page.xhtml src/content/ko/administrator-manual/general/system/jobs.mdx --public-dir=public --attachment-dir=/administrator-manual/general/system/jobs
echo 'Converted 544211220 to src/content/ko/administrator-manual/general/system/jobs.mdx'

mkdir -p src/content/ko/administrator-manual
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544379638/page.xhtml src/content/ko/administrator-manual/databases.mdx --public-dir=public --attachment-dir=/administrator-manual/databases
echo 'Converted 544379638 to src/content/ko/administrator-manual/databases.mdx'

mkdir -p src/content/ko/administrator-manual/databases
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/956071939/page.xhtml src/content/ko/administrator-manual/databases/dac-general-configurations.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/dac-general-configurations
echo 'Converted 956071939 to src/content/ko/administrator-manual/databases/dac-general-configurations.mdx'

mkdir -p src/content/ko/administrator-manual/databases/dac-general-configurations
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/921436219/page.xhtml src/content/ko/administrator-manual/databases/dac-general-configurations/unmasking-zones.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/dac-general-configurations/unmasking-zones
echo 'Converted 921436219 to src/content/ko/administrator-manual/databases/dac-general-configurations/unmasking-zones.mdx'

mkdir -p src/content/ko/administrator-manual/databases/dac-general-configurations
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/1275396097/page.xhtml src/content/ko/administrator-manual/databases/dac-general-configurations/masking-pattern-menu-relocated.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/dac-general-configurations/masking-pattern-menu-relocated
echo 'Converted 1275396097 to src/content/ko/administrator-manual/databases/dac-general-configurations/masking-pattern-menu-relocated.mdx'

mkdir -p src/content/ko/administrator-manual/databases
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544379705/page.xhtml src/content/ko/administrator-manual/databases/connection-management.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/connection-management
echo 'Converted 544379705 to src/content/ko/administrator-manual/databases/connection-management.mdx'

mkdir -p src/content/ko/administrator-manual/databases/connection-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544145672/page.xhtml src/content/ko/administrator-manual/databases/connection-management/cloud-providers.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/connection-management/cloud-providers
echo 'Converted 544145672 to src/content/ko/administrator-manual/databases/connection-management/cloud-providers.mdx'

mkdir -p src/content/ko/administrator-manual/databases/connection-management/cloud-providers
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544379719/page.xhtml src/content/ko/administrator-manual/databases/connection-management/cloud-providers/synchronizing-db-resources-from-aws.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/connection-management/cloud-providers/synchronizing-db-resources-from-aws
echo 'Converted 544379719 to src/content/ko/administrator-manual/databases/connection-management/cloud-providers/synchronizing-db-resources-from-aws.mdx'

mkdir -p src/content/ko/administrator-manual/databases/connection-management/cloud-providers
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/562167871/page.xhtml src/content/ko/administrator-manual/databases/connection-management/cloud-providers/synchronizing-db-resources-from-ms-azure.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/connection-management/cloud-providers/synchronizing-db-resources-from-ms-azure
echo 'Converted 562167871 to src/content/ko/administrator-manual/databases/connection-management/cloud-providers/synchronizing-db-resources-from-ms-azure.mdx'

mkdir -p src/content/ko/administrator-manual/databases/connection-management/cloud-providers
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/562167809/page.xhtml src/content/ko/administrator-manual/databases/connection-management/cloud-providers/synchronizing-db-resources-from-google-cloud.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/connection-management/cloud-providers/synchronizing-db-resources-from-google-cloud
echo 'Converted 562167809 to src/content/ko/administrator-manual/databases/connection-management/cloud-providers/synchronizing-db-resources-from-google-cloud.mdx'

mkdir -p src/content/ko/administrator-manual/databases/connection-management/cloud-providers
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/712507393/page.xhtml src/content/ko/administrator-manual/databases/connection-management/cloud-providers/verifying-cloud-synchronization-settings-with-dry-run-feature.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/connection-management/cloud-providers/verifying-cloud-synchronization-settings-with-dry-run-feature
echo 'Converted 712507393 to src/content/ko/administrator-manual/databases/connection-management/cloud-providers/verifying-cloud-synchronization-settings-with-dry-run-feature.mdx'

mkdir -p src/content/ko/administrator-manual/databases/connection-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544014712/page.xhtml src/content/ko/administrator-manual/databases/connection-management/db-connections.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/connection-management/db-connections
echo 'Converted 544014712 to src/content/ko/administrator-manual/databases/connection-management/db-connections.mdx'

mkdir -p src/content/ko/administrator-manual/databases/connection-management/db-connections
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544380381/page.xhtml src/content/ko/administrator-manual/databases/connection-management/db-connections/mongodb-specific-guide.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/connection-management/db-connections/mongodb-specific-guide
echo 'Converted 544380381 to src/content/ko/administrator-manual/databases/connection-management/db-connections/mongodb-specific-guide.mdx'

mkdir -p src/content/ko/administrator-manual/databases/connection-management/db-connections
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/568852692/page.xhtml src/content/ko/administrator-manual/databases/connection-management/db-connections/documentdb-specific-guide.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/connection-management/db-connections/documentdb-specific-guide
echo 'Converted 568852692 to src/content/ko/administrator-manual/databases/connection-management/db-connections/documentdb-specific-guide.mdx'

mkdir -p src/content/ko/administrator-manual/databases/connection-management/db-connections
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/811434142/page.xhtml src/content/ko/administrator-manual/databases/connection-management/db-connections/google-bigquery-oauth-authentication-configuration.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/connection-management/db-connections/google-bigquery-oauth-authentication-configuration
echo 'Converted 811434142 to src/content/ko/administrator-manual/databases/connection-management/db-connections/google-bigquery-oauth-authentication-configuration.mdx'

mkdir -p src/content/ko/administrator-manual/databases/connection-management/db-connections
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/820806182/page.xhtml src/content/ko/administrator-manual/databases/connection-management/db-connections/aws-athena-specific-guide.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/connection-management/db-connections/aws-athena-specific-guide
echo 'Converted 820806182 to src/content/ko/administrator-manual/databases/connection-management/db-connections/aws-athena-specific-guide.mdx'

mkdir -p src/content/ko/administrator-manual/databases/connection-management/db-connections
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/880082945/page.xhtml src/content/ko/administrator-manual/databases/connection-management/db-connections/custom-data-source-configuration-and-log-verification.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/connection-management/db-connections/custom-data-source-configuration-and-log-verification
echo 'Converted 880082945 to src/content/ko/administrator-manual/databases/connection-management/db-connections/custom-data-source-configuration-and-log-verification.mdx'

mkdir -p src/content/ko/administrator-manual/databases/connection-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544145691/page.xhtml src/content/ko/administrator-manual/databases/connection-management/ssl-configurations.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/connection-management/ssl-configurations
echo 'Converted 544145691 to src/content/ko/administrator-manual/databases/connection-management/ssl-configurations.mdx'

mkdir -p src/content/ko/administrator-manual/databases/connection-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544047436/page.xhtml src/content/ko/administrator-manual/databases/connection-management/ssh-configurations.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/connection-management/ssh-configurations
echo 'Converted 544047436 to src/content/ko/administrator-manual/databases/connection-management/ssh-configurations.mdx'

mkdir -p src/content/ko/administrator-manual/databases/connection-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544112932/page.xhtml src/content/ko/administrator-manual/databases/connection-management/kerberos-configurations.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/connection-management/kerberos-configurations
echo 'Converted 544112932 to src/content/ko/administrator-manual/databases/connection-management/kerberos-configurations.mdx'

mkdir -p src/content/ko/administrator-manual/databases
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544380126/page.xhtml src/content/ko/administrator-manual/databases/db-access-control.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/db-access-control
echo 'Converted 544380126 to src/content/ko/administrator-manual/databases/db-access-control.mdx'

mkdir -p src/content/ko/administrator-manual/databases/db-access-control
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544380140/page.xhtml src/content/ko/administrator-manual/databases/db-access-control/privilege-type.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/db-access-control/privilege-type
echo 'Converted 544380140 to src/content/ko/administrator-manual/databases/db-access-control/privilege-type.mdx'

mkdir -p src/content/ko/administrator-manual/databases/db-access-control
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544380173/page.xhtml src/content/ko/administrator-manual/databases/db-access-control/access-control.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/db-access-control/access-control
echo 'Converted 544380173 to src/content/ko/administrator-manual/databases/db-access-control/access-control.mdx'

mkdir -p src/content/ko/administrator-manual/databases
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544379868/page.xhtml src/content/ko/administrator-manual/databases/policies.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/policies
echo 'Converted 544379868 to src/content/ko/administrator-manual/databases/policies.mdx'

mkdir -p src/content/ko/administrator-manual/databases/policies
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544379937/page.xhtml src/content/ko/administrator-manual/databases/policies/data-access.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/policies/data-access
echo 'Converted 544379937 to src/content/ko/administrator-manual/databases/policies/data-access.mdx'

mkdir -p src/content/ko/administrator-manual/databases/policies
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/569376769/page.xhtml src/content/ko/administrator-manual/databases/policies/masking-pattern.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/policies/masking-pattern
echo 'Converted 569376769 to src/content/ko/administrator-manual/databases/policies/masking-pattern.mdx'

mkdir -p src/content/ko/administrator-manual/databases/policies
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544379882/page.xhtml src/content/ko/administrator-manual/databases/policies/data-masking.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/policies/data-masking
echo 'Converted 544379882 to src/content/ko/administrator-manual/databases/policies/data-masking.mdx'

mkdir -p src/content/ko/administrator-manual/databases/policies
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544379993/page.xhtml src/content/ko/administrator-manual/databases/policies/sensitive-data.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/policies/sensitive-data
echo 'Converted 544379993 to src/content/ko/administrator-manual/databases/policies/sensitive-data.mdx'

mkdir -p src/content/ko/administrator-manual/databases/policies
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/713129986/page.xhtml src/content/ko/administrator-manual/databases/policies/policy-exception.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/policies/policy-exception
echo 'Converted 713129986 to src/content/ko/administrator-manual/databases/policies/policy-exception.mdx'

mkdir -p src/content/ko/administrator-manual/databases
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/571277577/page.xhtml src/content/ko/administrator-manual/databases/ledger-management.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/ledger-management
echo 'Converted 571277577 to src/content/ko/administrator-manual/databases/ledger-management.mdx'

mkdir -p src/content/ko/administrator-manual/databases/ledger-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544380061/page.xhtml src/content/ko/administrator-manual/databases/ledger-management/ledger-table-policy.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/ledger-management/ledger-table-policy
echo 'Converted 544380061 to src/content/ko/administrator-manual/databases/ledger-management/ledger-table-policy.mdx'

mkdir -p src/content/ko/administrator-manual/databases/ledger-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/571277650/page.xhtml src/content/ko/administrator-manual/databases/ledger-management/ledger-approval-rules.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/ledger-management/ledger-approval-rules
echo 'Converted 571277650 to src/content/ko/administrator-manual/databases/ledger-management/ledger-approval-rules.mdx'

mkdir -p src/content/ko/administrator-manual/databases
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/873136365/page.xhtml src/content/ko/administrator-manual/databases/new-policy-management.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/new-policy-management
echo 'Converted 873136365 to src/content/ko/administrator-manual/databases/new-policy-management.mdx'

mkdir -p src/content/ko/administrator-manual/databases/new-policy-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/878805502/page.xhtml src/content/ko/administrator-manual/databases/new-policy-management/data-paths.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/new-policy-management/data-paths
echo 'Converted 878805502 to src/content/ko/administrator-manual/databases/new-policy-management/data-paths.mdx'

mkdir -p src/content/ko/administrator-manual/databases/new-policy-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/879198569/page.xhtml src/content/ko/administrator-manual/databases/new-policy-management/data-policies.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/new-policy-management/data-policies
echo 'Converted 879198569 to src/content/ko/administrator-manual/databases/new-policy-management/data-policies.mdx'

mkdir -p src/content/ko/administrator-manual/databases/new-policy-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/1064796485/page.xhtml src/content/ko/administrator-manual/databases/new-policy-management/exception-management.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/new-policy-management/exception-management
echo 'Converted 1064796485 to src/content/ko/administrator-manual/databases/new-policy-management/exception-management.mdx'

mkdir -p src/content/ko/administrator-manual/databases
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/954139156/page.xhtml src/content/ko/administrator-manual/databases/monitoring.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/monitoring
echo 'Converted 954139156 to src/content/ko/administrator-manual/databases/monitoring.mdx'

mkdir -p src/content/ko/administrator-manual/databases/monitoring
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/954172219/page.xhtml src/content/ko/administrator-manual/databases/monitoring/running-queries.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/monitoring/running-queries
echo 'Converted 954172219 to src/content/ko/administrator-manual/databases/monitoring/running-queries.mdx'

mkdir -p src/content/ko/administrator-manual/databases/monitoring
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/954204974/page.xhtml src/content/ko/administrator-manual/databases/monitoring/proxy-management.mdx --public-dir=public --attachment-dir=/administrator-manual/databases/monitoring/proxy-management
echo 'Converted 954204974 to src/content/ko/administrator-manual/databases/monitoring/proxy-management.mdx'

mkdir -p src/content/ko/administrator-manual
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544380588/page.xhtml src/content/ko/administrator-manual/servers.mdx --public-dir=public --attachment-dir=/administrator-manual/servers
echo 'Converted 544380588 to src/content/ko/administrator-manual/servers.mdx'

mkdir -p src/content/ko/administrator-manual/servers
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/954336174/page.xhtml src/content/ko/administrator-manual/servers/sac-general-configurations.mdx --public-dir=public --attachment-dir=/administrator-manual/servers/sac-general-configurations
echo 'Converted 954336174 to src/content/ko/administrator-manual/servers/sac-general-configurations.mdx'

mkdir -p src/content/ko/administrator-manual/servers
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544380635/page.xhtml src/content/ko/administrator-manual/servers/connection-management.mdx --public-dir=public --attachment-dir=/administrator-manual/servers/connection-management
echo 'Converted 544380635 to src/content/ko/administrator-manual/servers/connection-management.mdx'

mkdir -p src/content/ko/administrator-manual/servers/connection-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544178567/page.xhtml src/content/ko/administrator-manual/servers/connection-management/cloud-providers.mdx --public-dir=public --attachment-dir=/administrator-manual/servers/connection-management/cloud-providers
echo 'Converted 544178567 to src/content/ko/administrator-manual/servers/connection-management/cloud-providers.mdx'

mkdir -p src/content/ko/administrator-manual/servers/connection-management/cloud-providers
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544380650/page.xhtml src/content/ko/administrator-manual/servers/connection-management/cloud-providers/synchronizing-server-resources-from-aws.mdx --public-dir=public --attachment-dir=/administrator-manual/servers/connection-management/cloud-providers/synchronizing-server-resources-from-aws
echo 'Converted 544380650 to src/content/ko/administrator-manual/servers/connection-management/cloud-providers/synchronizing-server-resources-from-aws.mdx'

mkdir -p src/content/ko/administrator-manual/servers/connection-management/cloud-providers
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544380741/page.xhtml src/content/ko/administrator-manual/servers/connection-management/cloud-providers/synchronizing-server-resources-from-azure.mdx --public-dir=public --attachment-dir=/administrator-manual/servers/connection-management/cloud-providers/synchronizing-server-resources-from-azure
echo 'Converted 544380741 to src/content/ko/administrator-manual/servers/connection-management/cloud-providers/synchronizing-server-resources-from-azure.mdx'

mkdir -p src/content/ko/administrator-manual/servers/connection-management/cloud-providers
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544380708/page.xhtml src/content/ko/administrator-manual/servers/connection-management/cloud-providers/synchronizing-server-resources-from-gcp.mdx --public-dir=public --attachment-dir=/administrator-manual/servers/connection-management/cloud-providers/synchronizing-server-resources-from-gcp
echo 'Converted 544380708 to src/content/ko/administrator-manual/servers/connection-management/cloud-providers/synchronizing-server-resources-from-gcp.mdx'

mkdir -p src/content/ko/administrator-manual/servers/connection-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544211361/page.xhtml src/content/ko/administrator-manual/servers/connection-management/servers.mdx --public-dir=public --attachment-dir=/administrator-manual/servers/connection-management/servers
echo 'Converted 544211361 to src/content/ko/administrator-manual/servers/connection-management/servers.mdx'

mkdir -p src/content/ko/administrator-manual/servers/connection-management/servers
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544380774/page.xhtml src/content/ko/administrator-manual/servers/connection-management/servers/manually-registering-individual-servers.mdx --public-dir=public --attachment-dir=/administrator-manual/servers/connection-management/servers/manually-registering-individual-servers
echo 'Converted 544380774 to src/content/ko/administrator-manual/servers/connection-management/servers/manually-registering-individual-servers.mdx'

mkdir -p src/content/ko/administrator-manual/servers/connection-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544080186/page.xhtml src/content/ko/administrator-manual/servers/connection-management/server-groups.mdx --public-dir=public --attachment-dir=/administrator-manual/servers/connection-management/server-groups
echo 'Converted 544080186 to src/content/ko/administrator-manual/servers/connection-management/server-groups.mdx'

mkdir -p src/content/ko/administrator-manual/servers/connection-management/server-groups
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544380846/page.xhtml src/content/ko/administrator-manual/servers/connection-management/server-groups/managing-servers-as-groups.mdx --public-dir=public --attachment-dir=/administrator-manual/servers/connection-management/server-groups/managing-servers-as-groups
echo 'Converted 544380846 to src/content/ko/administrator-manual/servers/connection-management/server-groups/managing-servers-as-groups.mdx'

mkdir -p src/content/ko/administrator-manual/servers/connection-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544211376/page.xhtml src/content/ko/administrator-manual/servers/connection-management/server-agents-for-rdp.mdx --public-dir=public --attachment-dir=/administrator-manual/servers/connection-management/server-agents-for-rdp
echo 'Converted 544211376 to src/content/ko/administrator-manual/servers/connection-management/server-agents-for-rdp.mdx'

mkdir -p src/content/ko/administrator-manual/servers/connection-management/server-agents-for-rdp
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/565575990/page.xhtml src/content/ko/administrator-manual/servers/connection-management/server-agents-for-rdp/installing-and-removing-server-agent.mdx --public-dir=public --attachment-dir=/administrator-manual/servers/connection-management/server-agents-for-rdp/installing-and-removing-server-agent
echo 'Converted 565575990 to src/content/ko/administrator-manual/servers/connection-management/server-agents-for-rdp/installing-and-removing-server-agent.mdx'

mkdir -p src/content/ko/administrator-manual/servers/connection-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/615710737/page.xhtml src/content/ko/administrator-manual/servers/connection-management/proxyjump-configurations.mdx --public-dir=public --attachment-dir=/administrator-manual/servers/connection-management/proxyjump-configurations
echo 'Converted 615710737 to src/content/ko/administrator-manual/servers/connection-management/proxyjump-configurations.mdx'

mkdir -p src/content/ko/administrator-manual/servers/connection-management/proxyjump-configurations
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/615743551/page.xhtml src/content/ko/administrator-manual/servers/connection-management/proxyjump-configurations/creating-proxyjump.mdx --public-dir=public --attachment-dir=/administrator-manual/servers/connection-management/proxyjump-configurations/creating-proxyjump
echo 'Converted 615743551 to src/content/ko/administrator-manual/servers/connection-management/proxyjump-configurations/creating-proxyjump.mdx'

mkdir -p src/content/ko/administrator-manual/servers
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/613777446/page.xhtml src/content/ko/administrator-manual/servers/server-account-management.mdx --public-dir=public --attachment-dir=/administrator-manual/servers/server-account-management
echo 'Converted 613777446 to src/content/ko/administrator-manual/servers/server-account-management.mdx'

mkdir -p src/content/ko/administrator-manual/servers/server-account-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544380991/page.xhtml src/content/ko/administrator-manual/servers/server-account-management/server-account-templates.mdx --public-dir=public --attachment-dir=/administrator-manual/servers/server-account-management/server-account-templates
echo 'Converted 544380991 to src/content/ko/administrator-manual/servers/server-account-management/server-account-templates.mdx'

mkdir -p src/content/ko/administrator-manual/servers/server-account-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544380960/page.xhtml src/content/ko/administrator-manual/servers/server-account-management/ssh-key-configurations.mdx --public-dir=public --attachment-dir=/administrator-manual/servers/server-account-management/ssh-key-configurations
echo 'Converted 544380960 to src/content/ko/administrator-manual/servers/server-account-management/ssh-key-configurations.mdx'

mkdir -p src/content/ko/administrator-manual/servers/server-account-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/615743501/page.xhtml src/content/ko/administrator-manual/servers/server-account-management/account-management.mdx --public-dir=public --attachment-dir=/administrator-manual/servers/server-account-management/account-management
echo 'Converted 615743501 to src/content/ko/administrator-manual/servers/server-account-management/account-management.mdx'

mkdir -p src/content/ko/administrator-manual/servers/server-account-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/615677962/page.xhtml src/content/ko/administrator-manual/servers/server-account-management/password-provisioning.mdx --public-dir=public --attachment-dir=/administrator-manual/servers/server-account-management/password-provisioning
echo 'Converted 615677962 to src/content/ko/administrator-manual/servers/server-account-management/password-provisioning.mdx'

mkdir -p src/content/ko/administrator-manual/servers/server-account-management/password-provisioning
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/619380898/page.xhtml src/content/ko/administrator-manual/servers/server-account-management/password-provisioning/creating-password-change-job.mdx --public-dir=public --attachment-dir=/administrator-manual/servers/server-account-management/password-provisioning/creating-password-change-job
echo 'Converted 619380898 to src/content/ko/administrator-manual/servers/server-account-management/password-provisioning/creating-password-change-job.mdx'

mkdir -p src/content/ko/administrator-manual/servers
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/543949216/page.xhtml src/content/ko/administrator-manual/servers/server-access-control.mdx --public-dir=public --attachment-dir=/administrator-manual/servers/server-access-control
echo 'Converted 543949216 to src/content/ko/administrator-manual/servers/server-access-control.mdx'

mkdir -p src/content/ko/administrator-manual/servers/server-access-control
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544381186/page.xhtml src/content/ko/administrator-manual/servers/server-access-control/access-control.mdx --public-dir=public --attachment-dir=/administrator-manual/servers/server-access-control/access-control
echo 'Converted 544381186 to src/content/ko/administrator-manual/servers/server-access-control/access-control.mdx'

mkdir -p src/content/ko/administrator-manual/servers/server-access-control/access-control
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544381282/page.xhtml src/content/ko/administrator-manual/servers/server-access-control/access-control/granting-and-revoking-permissions.mdx --public-dir=public --attachment-dir=/administrator-manual/servers/server-access-control/access-control/granting-and-revoking-permissions
echo 'Converted 544381282 to src/content/ko/administrator-manual/servers/server-access-control/access-control/granting-and-revoking-permissions.mdx'

mkdir -p src/content/ko/administrator-manual/servers/server-access-control/access-control
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544381200/page.xhtml src/content/ko/administrator-manual/servers/server-access-control/access-control/granting-and-revoking-roles.mdx --public-dir=public --attachment-dir=/administrator-manual/servers/server-access-control/access-control/granting-and-revoking-roles
echo 'Converted 544381200 to src/content/ko/administrator-manual/servers/server-access-control/access-control/granting-and-revoking-roles.mdx'

mkdir -p src/content/ko/administrator-manual/servers/server-access-control/access-control
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/878838349/page.xhtml src/content/ko/administrator-manual/servers/server-access-control/access-control/granting-server-privilege.mdx --public-dir=public --attachment-dir=/administrator-manual/servers/server-access-control/access-control/granting-server-privilege
echo 'Converted 878838349 to src/content/ko/administrator-manual/servers/server-access-control/access-control/granting-server-privilege.mdx'

mkdir -p src/content/ko/administrator-manual/servers/server-access-control
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544381150/page.xhtml src/content/ko/administrator-manual/servers/server-access-control/roles.mdx --public-dir=public --attachment-dir=/administrator-manual/servers/server-access-control/roles
echo 'Converted 544381150 to src/content/ko/administrator-manual/servers/server-access-control/roles.mdx'

mkdir -p src/content/ko/administrator-manual/servers/server-access-control
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544381025/page.xhtml src/content/ko/administrator-manual/servers/server-access-control/policies.mdx --public-dir=public --attachment-dir=/administrator-manual/servers/server-access-control/policies
echo 'Converted 544381025 to src/content/ko/administrator-manual/servers/server-access-control/policies.mdx'

mkdir -p src/content/ko/administrator-manual/servers/server-access-control/policies
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544381039/page.xhtml src/content/ko/administrator-manual/servers/server-access-control/policies/setting-server-access-policy.mdx --public-dir=public --attachment-dir=/administrator-manual/servers/server-access-control/policies/setting-server-access-policy
echo 'Converted 544381039 to src/content/ko/administrator-manual/servers/server-access-control/policies/setting-server-access-policy.mdx'

mkdir -p src/content/ko/administrator-manual/servers/server-access-control/policies
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544377895/page.xhtml src/content/ko/administrator-manual/servers/server-access-control/policies/enabling-server-proxy.mdx --public-dir=public --attachment-dir=/administrator-manual/servers/server-access-control/policies/enabling-server-proxy
echo 'Converted 544377895 to src/content/ko/administrator-manual/servers/server-access-control/policies/enabling-server-proxy.mdx'

mkdir -p src/content/ko/administrator-manual/servers/server-access-control
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544381118/page.xhtml src/content/ko/administrator-manual/servers/server-access-control/command-templates.mdx --public-dir=public --attachment-dir=/administrator-manual/servers/server-access-control/command-templates
echo 'Converted 544381118 to src/content/ko/administrator-manual/servers/server-access-control/command-templates.mdx'

mkdir -p src/content/ko/administrator-manual/servers/server-access-control
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544244109/page.xhtml src/content/ko/administrator-manual/servers/server-access-control/blocked-accounts.mdx --public-dir=public --attachment-dir=/administrator-manual/servers/server-access-control/blocked-accounts
echo 'Converted 544244109 to src/content/ko/administrator-manual/servers/server-access-control/blocked-accounts.mdx'

mkdir -p src/content/ko/administrator-manual
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544381596/page.xhtml src/content/ko/administrator-manual/kubernetes.mdx --public-dir=public --attachment-dir=/administrator-manual/kubernetes
echo 'Converted 544381596 to src/content/ko/administrator-manual/kubernetes.mdx'

mkdir -p src/content/ko/administrator-manual/kubernetes
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/954172232/page.xhtml src/content/ko/administrator-manual/kubernetes/kac-general-configurations.mdx --public-dir=public --attachment-dir=/administrator-manual/kubernetes/kac-general-configurations
echo 'Converted 954172232 to src/content/ko/administrator-manual/kubernetes/kac-general-configurations.mdx'

mkdir -p src/content/ko/administrator-manual/kubernetes
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544381637/page.xhtml src/content/ko/administrator-manual/kubernetes/connection-management.mdx --public-dir=public --attachment-dir=/administrator-manual/kubernetes/connection-management
echo 'Converted 544381637 to src/content/ko/administrator-manual/kubernetes/connection-management.mdx'

mkdir -p src/content/ko/administrator-manual/kubernetes/connection-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544381651/page.xhtml src/content/ko/administrator-manual/kubernetes/connection-management/cloud-providers.mdx --public-dir=public --attachment-dir=/administrator-manual/kubernetes/connection-management/cloud-providers
echo 'Converted 544381651 to src/content/ko/administrator-manual/kubernetes/connection-management/cloud-providers.mdx'

mkdir -p src/content/ko/administrator-manual/kubernetes/connection-management/cloud-providers
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544381739/page.xhtml src/content/ko/administrator-manual/kubernetes/connection-management/cloud-providers/synchronizing-kubernetes-resources-from-aws.mdx --public-dir=public --attachment-dir=/administrator-manual/kubernetes/connection-management/cloud-providers/synchronizing-kubernetes-resources-from-aws
echo 'Converted 544381739 to src/content/ko/administrator-manual/kubernetes/connection-management/cloud-providers/synchronizing-kubernetes-resources-from-aws.mdx'

mkdir -p src/content/ko/administrator-manual/kubernetes/connection-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544381839/page.xhtml src/content/ko/administrator-manual/kubernetes/connection-management/clusters.mdx --public-dir=public --attachment-dir=/administrator-manual/kubernetes/connection-management/clusters
echo 'Converted 544381839 to src/content/ko/administrator-manual/kubernetes/connection-management/clusters.mdx'

mkdir -p src/content/ko/administrator-manual/kubernetes/connection-management/clusters
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544381877/page.xhtml src/content/ko/administrator-manual/kubernetes/connection-management/clusters/manually-registering-kubernetes-clusters.mdx --public-dir=public --attachment-dir=/administrator-manual/kubernetes/connection-management/clusters/manually-registering-kubernetes-clusters
echo 'Converted 544381877 to src/content/ko/administrator-manual/kubernetes/connection-management/clusters/manually-registering-kubernetes-clusters.mdx'

mkdir -p src/content/ko/administrator-manual/kubernetes
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544383110/page.xhtml src/content/ko/administrator-manual/kubernetes/k8s-access-control.mdx --public-dir=public --attachment-dir=/administrator-manual/kubernetes/k8s-access-control
echo 'Converted 544383110 to src/content/ko/administrator-manual/kubernetes/k8s-access-control.mdx'

mkdir -p src/content/ko/administrator-manual/kubernetes/k8s-access-control
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544383124/page.xhtml src/content/ko/administrator-manual/kubernetes/k8s-access-control/access-control.mdx --public-dir=public --attachment-dir=/administrator-manual/kubernetes/k8s-access-control/access-control
echo 'Converted 544383124 to src/content/ko/administrator-manual/kubernetes/k8s-access-control/access-control.mdx'

mkdir -p src/content/ko/administrator-manual/kubernetes/k8s-access-control/access-control
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544383381/page.xhtml src/content/ko/administrator-manual/kubernetes/k8s-access-control/access-control/granting-and-revoking-kubernetes-roles.mdx --public-dir=public --attachment-dir=/administrator-manual/kubernetes/k8s-access-control/access-control/granting-and-revoking-kubernetes-roles
echo 'Converted 544383381 to src/content/ko/administrator-manual/kubernetes/k8s-access-control/access-control/granting-and-revoking-kubernetes-roles.mdx'

mkdir -p src/content/ko/administrator-manual/kubernetes/k8s-access-control
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544382741/page.xhtml src/content/ko/administrator-manual/kubernetes/k8s-access-control/roles.mdx --public-dir=public --attachment-dir=/administrator-manual/kubernetes/k8s-access-control/roles
echo 'Converted 544382741 to src/content/ko/administrator-manual/kubernetes/k8s-access-control/roles.mdx'

mkdir -p src/content/ko/administrator-manual/kubernetes/k8s-access-control/roles
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544382963/page.xhtml src/content/ko/administrator-manual/kubernetes/k8s-access-control/roles/setting-kubernetes-roles.mdx --public-dir=public --attachment-dir=/administrator-manual/kubernetes/k8s-access-control/roles/setting-kubernetes-roles
echo 'Converted 544382963 to src/content/ko/administrator-manual/kubernetes/k8s-access-control/roles/setting-kubernetes-roles.mdx'

mkdir -p src/content/ko/administrator-manual/kubernetes/k8s-access-control
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544382060/page.xhtml src/content/ko/administrator-manual/kubernetes/k8s-access-control/policies.mdx --public-dir=public --attachment-dir=/administrator-manual/kubernetes/k8s-access-control/policies
echo 'Converted 544382060 to src/content/ko/administrator-manual/kubernetes/k8s-access-control/policies.mdx'

mkdir -p src/content/ko/administrator-manual/kubernetes/k8s-access-control/policies
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544382274/page.xhtml src/content/ko/administrator-manual/kubernetes/k8s-access-control/policies/setting-kubernetes-policies.mdx --public-dir=public --attachment-dir=/administrator-manual/kubernetes/k8s-access-control/policies/setting-kubernetes-policies
echo 'Converted 544382274 to src/content/ko/administrator-manual/kubernetes/k8s-access-control/policies/setting-kubernetes-policies.mdx'

mkdir -p src/content/ko/administrator-manual/kubernetes/k8s-access-control/policies
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544382364/page.xhtml src/content/ko/administrator-manual/kubernetes/k8s-access-control/policies/kubernetes-policy-yaml-code-syntax-guide.mdx --public-dir=public --attachment-dir=/administrator-manual/kubernetes/k8s-access-control/policies/kubernetes-policy-yaml-code-syntax-guide
echo 'Converted 544382364 to src/content/ko/administrator-manual/kubernetes/k8s-access-control/policies/kubernetes-policy-yaml-code-syntax-guide.mdx'

mkdir -p src/content/ko/administrator-manual/kubernetes/k8s-access-control/policies
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544382445/page.xhtml src/content/ko/administrator-manual/kubernetes/k8s-access-control/policies/kubernetes-policy-tips-guide.mdx --public-dir=public --attachment-dir=/administrator-manual/kubernetes/k8s-access-control/policies/kubernetes-policy-tips-guide
echo 'Converted 544382445 to src/content/ko/administrator-manual/kubernetes/k8s-access-control/policies/kubernetes-policy-tips-guide.mdx'

mkdir -p src/content/ko/administrator-manual/kubernetes/k8s-access-control/policies
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544382522/page.xhtml src/content/ko/administrator-manual/kubernetes/k8s-access-control/policies/kubernetes-policy-ui-code-helper-guide.mdx --public-dir=public --attachment-dir=/administrator-manual/kubernetes/k8s-access-control/policies/kubernetes-policy-ui-code-helper-guide
echo 'Converted 544382522 to src/content/ko/administrator-manual/kubernetes/k8s-access-control/policies/kubernetes-policy-ui-code-helper-guide.mdx'

mkdir -p src/content/ko/administrator-manual/kubernetes/k8s-access-control/policies
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544382659/page.xhtml src/content/ko/administrator-manual/kubernetes/k8s-access-control/policies/kubernetes-policy-action-configuration-reference-guide.mdx --public-dir=public --attachment-dir=/administrator-manual/kubernetes/k8s-access-control/policies/kubernetes-policy-action-configuration-reference-guide
echo 'Converted 544382659 to src/content/ko/administrator-manual/kubernetes/k8s-access-control/policies/kubernetes-policy-action-configuration-reference-guide.mdx'

mkdir -p src/content/ko/administrator-manual
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/783515900/page.xhtml src/content/ko/administrator-manual/web-apps.mdx --public-dir=public --attachment-dir=/administrator-manual/web-apps
echo 'Converted 783515900 to src/content/ko/administrator-manual/web-apps.mdx'

mkdir -p src/content/ko/administrator-manual/web-apps
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/1064829276/page.xhtml src/content/ko/administrator-manual/web-apps/connection-management.mdx --public-dir=public --attachment-dir=/administrator-manual/web-apps/connection-management
echo 'Converted 1064829276 to src/content/ko/administrator-manual/web-apps/connection-management.mdx'

mkdir -p src/content/ko/administrator-manual/web-apps/connection-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/1070694423/page.xhtml src/content/ko/administrator-manual/web-apps/connection-management/web-apps.mdx --public-dir=public --attachment-dir=/administrator-manual/web-apps/connection-management/web-apps
echo 'Converted 1070694423 to src/content/ko/administrator-manual/web-apps/connection-management/web-apps.mdx'

mkdir -p src/content/ko/administrator-manual/web-apps/connection-management
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/1064829246/page.xhtml src/content/ko/administrator-manual/web-apps/connection-management/web-app-configurations.mdx --public-dir=public --attachment-dir=/administrator-manual/web-apps/connection-management/web-app-configurations
echo 'Converted 1064829246 to src/content/ko/administrator-manual/web-apps/connection-management/web-app-configurations.mdx'

mkdir -p src/content/ko/administrator-manual/web-apps
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/1070596135/page.xhtml src/content/ko/administrator-manual/web-apps/web-app-access-control.mdx --public-dir=public --attachment-dir=/administrator-manual/web-apps/web-app-access-control
echo 'Converted 1070596135 to src/content/ko/administrator-manual/web-apps/web-app-access-control.mdx'

mkdir -p src/content/ko/administrator-manual/web-apps/web-app-access-control
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/1070628904/page.xhtml src/content/ko/administrator-manual/web-apps/web-app-access-control/access-control.mdx --public-dir=public --attachment-dir=/administrator-manual/web-apps/web-app-access-control/access-control
echo 'Converted 1070628904 to src/content/ko/administrator-manual/web-apps/web-app-access-control/access-control.mdx'

mkdir -p src/content/ko/administrator-manual/web-apps/web-app-access-control/access-control
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/1064599910/page.xhtml src/content/ko/administrator-manual/web-apps/web-app-access-control/access-control/granting-and-revoking-roles.mdx --public-dir=public --attachment-dir=/administrator-manual/web-apps/web-app-access-control/access-control/granting-and-revoking-roles
echo 'Converted 1064599910 to src/content/ko/administrator-manual/web-apps/web-app-access-control/access-control/granting-and-revoking-roles.mdx'

mkdir -p src/content/ko/administrator-manual/web-apps/web-app-access-control
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/1070628923/page.xhtml src/content/ko/administrator-manual/web-apps/web-app-access-control/roles.mdx --public-dir=public --attachment-dir=/administrator-manual/web-apps/web-app-access-control/roles
echo 'Converted 1070628923 to src/content/ko/administrator-manual/web-apps/web-app-access-control/roles.mdx'

mkdir -p src/content/ko/administrator-manual/web-apps/web-app-access-control
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/1064829343/page.xhtml src/content/ko/administrator-manual/web-apps/web-app-access-control/policies.mdx --public-dir=public --attachment-dir=/administrator-manual/web-apps/web-app-access-control/policies
echo 'Converted 1064829343 to src/content/ko/administrator-manual/web-apps/web-app-access-control/policies.mdx'

mkdir -p src/content/ko/administrator-manual/web-apps
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/783417593/page.xhtml src/content/ko/administrator-manual/web-apps/wac-quickstart.mdx --public-dir=public --attachment-dir=/administrator-manual/web-apps/wac-quickstart
echo 'Converted 783417593 to src/content/ko/administrator-manual/web-apps/wac-quickstart.mdx'

mkdir -p src/content/ko/administrator-manual/web-apps/wac-quickstart
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/783745324/page.xhtml src/content/ko/administrator-manual/web-apps/wac-quickstart/1027-wac-role-policy-guide.mdx --public-dir=public --attachment-dir=/administrator-manual/web-apps/wac-quickstart/1027-wac-role-policy-guide
echo 'Converted 783745324 to src/content/ko/administrator-manual/web-apps/wac-quickstart/1027-wac-role-policy-guide.mdx'

mkdir -p src/content/ko/administrator-manual/web-apps/wac-quickstart
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/924287097/page.xhtml src/content/ko/administrator-manual/web-apps/wac-quickstart/1028-wac-rbac-guide.mdx --public-dir=public --attachment-dir=/administrator-manual/web-apps/wac-quickstart/1028-wac-rbac-guide
echo 'Converted 924287097 to src/content/ko/administrator-manual/web-apps/wac-quickstart/1028-wac-rbac-guide.mdx'

mkdir -p src/content/ko/administrator-manual/web-apps/wac-quickstart
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/956235931/page.xhtml src/content/ko/administrator-manual/web-apps/wac-quickstart/1030-wac-jit-permission-acquisition-guide.mdx --public-dir=public --attachment-dir=/administrator-manual/web-apps/wac-quickstart/1030-wac-jit-permission-acquisition-guide
echo 'Converted 956235931 to src/content/ko/administrator-manual/web-apps/wac-quickstart/1030-wac-jit-permission-acquisition-guide.mdx'

mkdir -p src/content/ko/administrator-manual/web-apps/wac-quickstart
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/805962425/page.xhtml src/content/ko/administrator-manual/web-apps/wac-quickstart/root-ca-certificate-installation-guide.mdx --public-dir=public --attachment-dir=/administrator-manual/web-apps/wac-quickstart/root-ca-certificate-installation-guide
echo 'Converted 805962425 to src/content/ko/administrator-manual/web-apps/wac-quickstart/root-ca-certificate-installation-guide.mdx'

mkdir -p src/content/ko/administrator-manual/web-apps/wac-quickstart
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/883654785/page.xhtml src/content/ko/administrator-manual/web-apps/wac-quickstart/initial-wac-setup-in-web-app-configurations.mdx --public-dir=public --attachment-dir=/administrator-manual/web-apps/wac-quickstart/initial-wac-setup-in-web-app-configurations
echo 'Converted 883654785 to src/content/ko/administrator-manual/web-apps/wac-quickstart/initial-wac-setup-in-web-app-configurations.mdx'

mkdir -p src/content/ko/administrator-manual/web-apps/wac-quickstart
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/924319936/page.xhtml src/content/ko/administrator-manual/web-apps/wac-quickstart/wac-troubleshooting-guide.mdx --public-dir=public --attachment-dir=/administrator-manual/web-apps/wac-quickstart/wac-troubleshooting-guide
echo 'Converted 924319936 to src/content/ko/administrator-manual/web-apps/wac-quickstart/wac-troubleshooting-guide.mdx'

mkdir -p src/content/ko/administrator-manual/web-apps/wac-quickstart
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/927629410/page.xhtml src/content/ko/administrator-manual/web-apps/wac-quickstart/wac-faq.mdx --public-dir=public --attachment-dir=/administrator-manual/web-apps/wac-quickstart/wac-faq
echo 'Converted 927629410 to src/content/ko/administrator-manual/web-apps/wac-quickstart/wac-faq.mdx'

mkdir -p src/content/ko/administrator-manual
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544379062/page.xhtml src/content/ko/administrator-manual/audit.mdx --public-dir=public --attachment-dir=/administrator-manual/audit
echo 'Converted 544379062 to src/content/ko/administrator-manual/audit.mdx'

mkdir -p src/content/ko/administrator-manual/audit
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/693043522/page.xhtml src/content/ko/administrator-manual/audit/reports.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/reports
echo 'Converted 693043522 to src/content/ko/administrator-manual/audit/reports.mdx'

mkdir -p src/content/ko/administrator-manual/audit/reports
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544384417/page.xhtml src/content/ko/administrator-manual/audit/reports/reports.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/reports/reports
echo 'Converted 544384417 to src/content/ko/administrator-manual/audit/reports/reports.mdx'

mkdir -p src/content/ko/administrator-manual/audit/reports
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544379140/page.xhtml src/content/ko/administrator-manual/audit/reports/audit-log-export.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/reports/audit-log-export
echo 'Converted 544379140 to src/content/ko/administrator-manual/audit/reports/audit-log-export.mdx'

mkdir -p src/content/ko/administrator-manual/audit
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544211450/page.xhtml src/content/ko/administrator-manual/audit/general-logs.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/general-logs
echo 'Converted 544211450 to src/content/ko/administrator-manual/audit/general-logs.mdx'

mkdir -p src/content/ko/administrator-manual/audit/general-logs
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544080230/page.xhtml src/content/ko/administrator-manual/audit/general-logs/user-access-history.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/general-logs/user-access-history
echo 'Converted 544080230 to src/content/ko/administrator-manual/audit/general-logs/user-access-history.mdx'

mkdir -p src/content/ko/administrator-manual/audit/general-logs
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544113108/page.xhtml src/content/ko/administrator-manual/audit/general-logs/activity-logs.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/general-logs/activity-logs
echo 'Converted 544113108 to src/content/ko/administrator-manual/audit/general-logs/activity-logs.mdx'

mkdir -p src/content/ko/administrator-manual/audit/general-logs
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544047557/page.xhtml src/content/ko/administrator-manual/audit/general-logs/admin-role-history.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/general-logs/admin-role-history
echo 'Converted 544047557 to src/content/ko/administrator-manual/audit/general-logs/admin-role-history.mdx'

mkdir -p src/content/ko/administrator-manual/audit/general-logs
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/705724442/page.xhtml src/content/ko/administrator-manual/audit/general-logs/workflow-logs.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/general-logs/workflow-logs
echo 'Converted 705724442 to src/content/ko/administrator-manual/audit/general-logs/workflow-logs.mdx'

mkdir -p src/content/ko/administrator-manual/audit/general-logs
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/775455036/page.xhtml src/content/ko/administrator-manual/audit/general-logs/reverse-tunnels.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/general-logs/reverse-tunnels
echo 'Converted 775455036 to src/content/ko/administrator-manual/audit/general-logs/reverse-tunnels.mdx'

mkdir -p src/content/ko/administrator-manual/audit/general-logs/reverse-tunnels
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/811434216/page.xhtml src/content/ko/administrator-manual/audit/general-logs/reverse-tunnels/communicating-with-servers-through-reverse-tunnel.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/general-logs/reverse-tunnels/communicating-with-servers-through-reverse-tunnel
echo 'Converted 811434216 to src/content/ko/administrator-manual/audit/general-logs/reverse-tunnels/communicating-with-servers-through-reverse-tunnel.mdx'

mkdir -p src/content/ko/administrator-manual/audit/general-logs/reverse-tunnels
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/811466988/page.xhtml src/content/ko/administrator-manual/audit/general-logs/reverse-tunnels/communicating-with-clusters-through-reverse-tunnel.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/general-logs/reverse-tunnels/communicating-with-clusters-through-reverse-tunnel
echo 'Converted 811466988 to src/content/ko/administrator-manual/audit/general-logs/reverse-tunnels/communicating-with-clusters-through-reverse-tunnel.mdx'

mkdir -p src/content/ko/administrator-manual/audit/general-logs/reverse-tunnels
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/955318273/page.xhtml src/content/ko/administrator-manual/audit/general-logs/reverse-tunnels/communicating-with-db-through-reverse-tunnel.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/general-logs/reverse-tunnels/communicating-with-db-through-reverse-tunnel
echo 'Converted 955318273 to src/content/ko/administrator-manual/audit/general-logs/reverse-tunnels/communicating-with-db-through-reverse-tunnel.mdx'

mkdir -p src/content/ko/administrator-manual/audit
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544080248/page.xhtml src/content/ko/administrator-manual/audit/database-logs.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/database-logs
echo 'Converted 544080248 to src/content/ko/administrator-manual/audit/database-logs.mdx'

mkdir -p src/content/ko/administrator-manual/audit/database-logs
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544113141/page.xhtml src/content/ko/administrator-manual/audit/database-logs/db-access-history.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/database-logs/db-access-history
echo 'Converted 544113141 to src/content/ko/administrator-manual/audit/database-logs/db-access-history.mdx'

mkdir -p src/content/ko/administrator-manual/audit/database-logs
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544244149/page.xhtml src/content/ko/administrator-manual/audit/database-logs/query-audit.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/database-logs/query-audit
echo 'Converted 544244149 to src/content/ko/administrator-manual/audit/database-logs/query-audit.mdx'

mkdir -p src/content/ko/administrator-manual/audit/database-logs
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544145819/page.xhtml src/content/ko/administrator-manual/audit/database-logs/running-queries.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/database-logs/running-queries
echo 'Converted 544145819 to src/content/ko/administrator-manual/audit/database-logs/running-queries.mdx'

mkdir -p src/content/ko/administrator-manual/audit/database-logs
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544244163/page.xhtml src/content/ko/administrator-manual/audit/database-logs/dml-snapshots.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/database-logs/dml-snapshots
echo 'Converted 544244163 to src/content/ko/administrator-manual/audit/database-logs/dml-snapshots.mdx'

mkdir -p src/content/ko/administrator-manual/audit/database-logs
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544014894/page.xhtml src/content/ko/administrator-manual/audit/database-logs/account-lock-history.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/database-logs/account-lock-history
echo 'Converted 544014894 to src/content/ko/administrator-manual/audit/database-logs/account-lock-history.mdx'

mkdir -p src/content/ko/administrator-manual/audit/database-logs
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544080264/page.xhtml src/content/ko/administrator-manual/audit/database-logs/access-control-logs.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/database-logs/access-control-logs
echo 'Converted 544080264 to src/content/ko/administrator-manual/audit/database-logs/access-control-logs.mdx'

mkdir -p src/content/ko/administrator-manual/audit/database-logs
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/1070694532/page.xhtml src/content/ko/administrator-manual/audit/database-logs/policy-audit-logs.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/database-logs/policy-audit-logs
echo 'Converted 1070694532 to src/content/ko/administrator-manual/audit/database-logs/policy-audit-logs.mdx'

mkdir -p src/content/ko/administrator-manual/audit/database-logs
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/1164705793/page.xhtml src/content/ko/administrator-manual/audit/database-logs/policy-exception-logs.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/database-logs/policy-exception-logs
echo 'Converted 1164705793 to src/content/ko/administrator-manual/audit/database-logs/policy-exception-logs.mdx'

mkdir -p src/content/ko/administrator-manual/audit
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544014907/page.xhtml src/content/ko/administrator-manual/audit/server-logs.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/server-logs
echo 'Converted 544014907 to src/content/ko/administrator-manual/audit/server-logs.mdx'

mkdir -p src/content/ko/administrator-manual/audit/server-logs
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544244182/page.xhtml src/content/ko/administrator-manual/audit/server-logs/server-access-history.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/server-logs/server-access-history
echo 'Converted 544244182 to src/content/ko/administrator-manual/audit/server-logs/server-access-history.mdx'

mkdir -p src/content/ko/administrator-manual/audit/server-logs
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544244208/page.xhtml src/content/ko/administrator-manual/audit/server-logs/command-audit.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/server-logs/command-audit
echo 'Converted 544244208 to src/content/ko/administrator-manual/audit/server-logs/command-audit.mdx'

mkdir -p src/content/ko/administrator-manual/audit/server-logs
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544014927/page.xhtml src/content/ko/administrator-manual/audit/server-logs/session-logs.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/server-logs/session-logs
echo 'Converted 544014927 to src/content/ko/administrator-manual/audit/server-logs/session-logs.mdx'

mkdir -p src/content/ko/administrator-manual/audit/server-logs
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544014940/page.xhtml src/content/ko/administrator-manual/audit/server-logs/session-monitoring.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/server-logs/session-monitoring
echo 'Converted 544014940 to src/content/ko/administrator-manual/audit/server-logs/session-monitoring.mdx'

mkdir -p src/content/ko/administrator-manual/audit/server-logs
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544244234/page.xhtml src/content/ko/administrator-manual/audit/server-logs/access-control-logs.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/server-logs/access-control-logs
echo 'Converted 544244234 to src/content/ko/administrator-manual/audit/server-logs/access-control-logs.mdx'

mkdir -p src/content/ko/administrator-manual/audit/server-logs
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544244244/page.xhtml src/content/ko/administrator-manual/audit/server-logs/server-role-history.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/server-logs/server-role-history
echo 'Converted 544244244 to src/content/ko/administrator-manual/audit/server-logs/server-role-history.mdx'

mkdir -p src/content/ko/administrator-manual/audit/server-logs
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/543949311/page.xhtml src/content/ko/administrator-manual/audit/server-logs/account-lock-history.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/server-logs/account-lock-history
echo 'Converted 543949311 to src/content/ko/administrator-manual/audit/server-logs/account-lock-history.mdx'

mkdir -p src/content/ko/administrator-manual/audit
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544383513/page.xhtml src/content/ko/administrator-manual/audit/kubernetes-logs.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/kubernetes-logs
echo 'Converted 544383513 to src/content/ko/administrator-manual/audit/kubernetes-logs.mdx'

mkdir -p src/content/ko/administrator-manual/audit/kubernetes-logs
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544383587/page.xhtml src/content/ko/administrator-manual/audit/kubernetes-logs/request-audit.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/kubernetes-logs/request-audit
echo 'Converted 544383587 to src/content/ko/administrator-manual/audit/kubernetes-logs/request-audit.mdx'

mkdir -p src/content/ko/administrator-manual/audit/kubernetes-logs
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544383693/page.xhtml src/content/ko/administrator-manual/audit/kubernetes-logs/pod-session-recordings.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/kubernetes-logs/pod-session-recordings
echo 'Converted 544383693 to src/content/ko/administrator-manual/audit/kubernetes-logs/pod-session-recordings.mdx'

mkdir -p src/content/ko/administrator-manual/audit/kubernetes-logs
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/544383799/page.xhtml src/content/ko/administrator-manual/audit/kubernetes-logs/kubernetes-role-history.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/kubernetes-logs/kubernetes-role-history
echo 'Converted 544383799 to src/content/ko/administrator-manual/audit/kubernetes-logs/kubernetes-role-history.mdx'

mkdir -p src/content/ko/administrator-manual/audit
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/1064829366/page.xhtml src/content/ko/administrator-manual/audit/web-app-logs.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/web-app-logs
echo 'Converted 1064829366 to src/content/ko/administrator-manual/audit/web-app-logs.mdx'

mkdir -p src/content/ko/administrator-manual/audit/web-app-logs
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/1064829380/page.xhtml src/content/ko/administrator-manual/audit/web-app-logs/web-access-history.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/web-app-logs/web-access-history
echo 'Converted 1064829380 to src/content/ko/administrator-manual/audit/web-app-logs/web-access-history.mdx'

mkdir -p src/content/ko/administrator-manual/audit/web-app-logs
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/1070563457/page.xhtml src/content/ko/administrator-manual/audit/web-app-logs/web-event-audit.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/web-app-logs/web-event-audit
echo 'Converted 1070563457 to src/content/ko/administrator-manual/audit/web-app-logs/web-event-audit.mdx'

mkdir -p src/content/ko/administrator-manual/audit/web-app-logs
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/1070694561/page.xhtml src/content/ko/administrator-manual/audit/web-app-logs/user-activity-recordings.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/web-app-logs/user-activity-recordings
echo 'Converted 1070694561 to src/content/ko/administrator-manual/audit/web-app-logs/user-activity-recordings.mdx'

mkdir -p src/content/ko/administrator-manual/audit/web-app-logs
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/1070563469/page.xhtml src/content/ko/administrator-manual/audit/web-app-logs/web-app-role-history.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/web-app-logs/web-app-role-history
echo 'Converted 1070563469 to src/content/ko/administrator-manual/audit/web-app-logs/web-app-role-history.mdx'

mkdir -p src/content/ko/administrator-manual/audit/web-app-logs
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/1070694552/page.xhtml src/content/ko/administrator-manual/audit/web-app-logs/jit-access-control-logs.mdx --public-dir=public --attachment-dir=/administrator-manual/audit/web-app-logs/jit-access-control-logs
echo 'Converted 1070694552 to src/content/ko/administrator-manual/audit/web-app-logs/jit-access-control-logs.mdx'

mkdir -p src/content/ko/administrator-manual
python confluence-mdx/bin/confluence_xhtml_to_markdown.py confluence-mdx/var/851280543/page.xhtml src/content/ko/administrator-manual/multi-agent-limitations.mdx --public-dir=public --attachment-dir=/administrator-manual/multi-agent-limitations
echo 'Converted 851280543 to src/content/ko/administrator-manual/multi-agent-limitations.mdx'

