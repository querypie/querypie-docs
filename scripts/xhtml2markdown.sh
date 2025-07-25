#!/usr/bin/env bash
# cd querypie-docs
# ./scripts/generate_commands_for_xhtml2markdown.py docs/latest-ko-confluence/list.en.txt

mkdir -p src/content/ko/querypie-manual
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/608501837/page.xhtml src/content/ko/querypie-manual/querypie-docs.mdx
echo 'Converted 608501837 to src/content/ko/querypie-manual/querypie-docs.mdx'

mkdir -p src/content/ko/.
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544375335/page.xhtml src/content/ko/./release-notes.mdx
echo 'Converted 544375335 to src/content/ko/./release-notes.mdx'

mkdir -p src/content/ko/release-notes
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/1064830173/page.xhtml src/content/ko/release-notes/1100.mdx
echo 'Converted 1064830173 to src/content/ko/release-notes/1100.mdx'

mkdir -p src/content/ko/release-notes
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/954335909/page.xhtml src/content/ko/release-notes/1030-1034.mdx
echo 'Converted 954335909 to src/content/ko/release-notes/1030-1034.mdx'

mkdir -p src/content/ko/release-notes
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/703463517/page.xhtml src/content/ko/release-notes/1020-10212.mdx
echo 'Converted 703463517 to src/content/ko/release-notes/1020-10212.mdx'

mkdir -p src/content/ko/release-notes
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/604995641/page.xhtml src/content/ko/release-notes/1010-10111.mdx
echo 'Converted 604995641 to src/content/ko/release-notes/1010-10111.mdx'

mkdir -p src/content/ko/release-notes
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544375355/page.xhtml src/content/ko/release-notes/1000-1002.mdx
echo 'Converted 544375355 to src/content/ko/release-notes/1000-1002.mdx'

mkdir -p src/content/ko/release-notes
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544375370/page.xhtml src/content/ko/release-notes/9200-9202.mdx
echo 'Converted 544375370 to src/content/ko/release-notes/9200-9202.mdx'

mkdir -p src/content/ko/release-notes
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544375385/page.xhtml src/content/ko/release-notes/9190.mdx
echo 'Converted 544375385 to src/content/ko/release-notes/9190.mdx'

mkdir -p src/content/ko/release-notes
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544375399/page.xhtml src/content/ko/release-notes/9180-9183.mdx
echo 'Converted 544375399 to src/content/ko/release-notes/9180-9183.mdx'

mkdir -p src/content/ko/release-notes
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544375414/page.xhtml src/content/ko/release-notes/9170-9171.mdx
echo 'Converted 544375414 to src/content/ko/release-notes/9170-9171.mdx'

mkdir -p src/content/ko/release-notes
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544375429/page.xhtml src/content/ko/release-notes/9160-9164.mdx
echo 'Converted 544375429 to src/content/ko/release-notes/9160-9164.mdx'

mkdir -p src/content/ko/release-notes
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544375443/page.xhtml src/content/ko/release-notes/9150-9154.mdx
echo 'Converted 544375443 to src/content/ko/release-notes/9150-9154.mdx'

mkdir -p src/content/ko/release-notes
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544375457/page.xhtml src/content/ko/release-notes/9140-9143.mdx
echo 'Converted 544375457 to src/content/ko/release-notes/9140-9143.mdx'

mkdir -p src/content/ko/release-notes
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544375471/page.xhtml src/content/ko/release-notes/9130-9135.mdx
echo 'Converted 544375471 to src/content/ko/release-notes/9130-9135.mdx'

mkdir -p src/content/ko/release-notes
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544375485/page.xhtml src/content/ko/release-notes/9120-91214.mdx
echo 'Converted 544375485 to src/content/ko/release-notes/9120-91214.mdx'

mkdir -p src/content/ko/release-notes/9120-91214
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544375505/page.xhtml src/content/ko/release-notes/9120-91214/menu-improvement-guide-9120.mdx
echo 'Converted 544375505 to src/content/ko/release-notes/9120-91214/menu-improvement-guide-9120.mdx'

mkdir -p src/content/ko/release-notes
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544375587/page.xhtml src/content/ko/release-notes/9110-9115.mdx
echo 'Converted 544375587 to src/content/ko/release-notes/9110-9115.mdx'

mkdir -p src/content/ko/release-notes
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544375607/page.xhtml src/content/ko/release-notes/9100-9104.mdx
echo 'Converted 544375607 to src/content/ko/release-notes/9100-9104.mdx'

mkdir -p src/content/ko/release-notes/9100-9104
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544375624/page.xhtml src/content/ko/release-notes/9100-9104/external-api-changes-9100-version.mdx
echo 'Converted 544375624 to src/content/ko/release-notes/9100-9104/external-api-changes-9100-version.mdx'

mkdir -p src/content/ko/release-notes
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544375659/page.xhtml src/content/ko/release-notes/990-998.mdx
echo 'Converted 544375659 to src/content/ko/release-notes/990-998.mdx'

mkdir -p src/content/ko/release-notes/990-998/external-api-changes-9810-version
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544375685/page.xhtml src/content/ko/release-notes/990-998/external-api-changes-9810-version/994-version.mdx
echo 'Converted 544375685 to src/content/ko/release-notes/990-998/external-api-changes-9810-version/994-version.mdx'

mkdir -p src/content/ko/release-notes/990-998/external-api-changes-994-version
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544375741/page.xhtml src/content/ko/release-notes/990-998/external-api-changes-994-version/995-version.mdx
echo 'Converted 544375741 to src/content/ko/release-notes/990-998/external-api-changes-994-version/995-version.mdx'

mkdir -p src/content/ko/release-notes
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544375768/page.xhtml src/content/ko/release-notes/980-9812.mdx
echo 'Converted 544375768 to src/content/ko/release-notes/980-9812.mdx'

mkdir -p src/content/ko/.
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544375784/page.xhtml src/content/ko/./querypie-overview.mdx
echo 'Converted 544375784 to src/content/ko/./querypie-overview.mdx'

mkdir -p src/content/ko/querypie-overview
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544112942/page.xhtml src/content/ko/querypie-overview/proxy-management.mdx
echo 'Converted 544112942 to src/content/ko/querypie-overview/proxy-management.mdx'

mkdir -p src/content/ko/querypie-overview/proxy-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544377869/page.xhtml src/content/ko/querypie-overview/proxy-management/enable-database-proxy.mdx
echo 'Converted 544377869 to src/content/ko/querypie-overview/proxy-management/enable-database-proxy.mdx'

mkdir -p src/content/ko/querypie-overview
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544375859/page.xhtml src/content/ko/querypie-overview/system-architecture-overview.mdx
echo 'Converted 544375859 to src/content/ko/querypie-overview/system-architecture-overview.mdx'

mkdir -p src/content/ko/querypie-overview
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544375808/page.xhtml src/content/ko/querypie-overview/installation-and-customer-support.mdx
echo 'Converted 544375808 to src/content/ko/querypie-overview/installation-and-customer-support.mdx'

mkdir -p src/content/ko/.
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544211126/page.xhtml src/content/ko/./user-manual.mdx
echo 'Converted 544211126 to src/content/ko/./user-manual.mdx'

mkdir -p src/content/ko/user-manual
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/578945174/page.xhtml src/content/ko/user-manual/my-dashboard.mdx
echo 'Converted 578945174 to src/content/ko/user-manual/my-dashboard.mdx'

mkdir -p src/content/ko/user-manual/my-dashboard
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/793542657/page.xhtml src/content/ko/user-manual/my-dashboard/user-password-reset-via-email.mdx
echo 'Converted 793542657 to src/content/ko/user-manual/my-dashboard/user-password-reset-via-email.mdx'

mkdir -p src/content/ko/user-manual
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544377922/page.xhtml src/content/ko/user-manual/workflow.mdx
echo 'Converted 544377922 to src/content/ko/user-manual/workflow.mdx'

mkdir -p src/content/ko/user-manual/workflow
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544377968/page.xhtml src/content/ko/user-manual/workflow/requesting-db-access.mdx
echo 'Converted 544377968 to src/content/ko/user-manual/workflow/requesting-db-access.mdx'

mkdir -p src/content/ko/user-manual/workflow
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544378069/page.xhtml src/content/ko/user-manual/workflow/requesting-sql.mdx
echo 'Converted 544378069 to src/content/ko/user-manual/workflow/requesting-sql.mdx'

mkdir -p src/content/ko/user-manual/workflow/requesting-sql
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/692355151/page.xhtml src/content/ko/user-manual/workflow/requesting-sql/using-execution-plan-explain-feature.mdx
echo 'Converted 692355151 to src/content/ko/user-manual/workflow/requesting-sql/using-execution-plan-explain-feature.mdx'

mkdir -p src/content/ko/user-manual/workflow
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544378182/page.xhtml src/content/ko/user-manual/workflow/requesting-sql-export.mdx
echo 'Converted 544378182 to src/content/ko/user-manual/workflow/requesting-sql-export.mdx'

mkdir -p src/content/ko/user-manual/workflow
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/712769539/page.xhtml src/content/ko/user-manual/workflow/requesting-unmasking-mask-removal-request.mdx
echo 'Converted 712769539 to src/content/ko/user-manual/workflow/requesting-unmasking-mask-removal-request.mdx'

mkdir -p src/content/ko/user-manual/workflow
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/1060306945/page.xhtml src/content/ko/user-manual/workflow/requesting-restricted-data-access.mdx
echo 'Converted 1060306945 to src/content/ko/user-manual/workflow/requesting-restricted-data-access.mdx'

mkdir -p src/content/ko/user-manual/workflow
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544378254/page.xhtml src/content/ko/user-manual/workflow/requesting-server-access.mdx
echo 'Converted 544378254 to src/content/ko/user-manual/workflow/requesting-server-access.mdx'

mkdir -p src/content/ko/user-manual/workflow
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/878936417/page.xhtml src/content/ko/user-manual/workflow/requesting-server-privilege.mdx
echo 'Converted 878936417 to src/content/ko/user-manual/workflow/requesting-server-privilege.mdx'

mkdir -p src/content/ko/user-manual/workflow
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544378348/page.xhtml src/content/ko/user-manual/workflow/requesting-access-role.mdx
echo 'Converted 544378348 to src/content/ko/user-manual/workflow/requesting-access-role.mdx'

mkdir -p src/content/ko/user-manual/workflow
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/1055358996/page.xhtml src/content/ko/user-manual/workflow/requesting-ip-registration.mdx
echo 'Converted 1055358996 to src/content/ko/user-manual/workflow/requesting-ip-registration.mdx'

mkdir -p src/content/ko/user-manual/workflow
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/568918170/page.xhtml src/content/ko/user-manual/workflow/approval-additional-features-proxy-approval-resubmission-etc.mdx
echo 'Converted 568918170 to src/content/ko/user-manual/workflow/approval-additional-features-proxy-approval-resubmission-etc.mdx'

mkdir -p src/content/ko/user-manual/workflow
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/1070006273/page.xhtml src/content/ko/user-manual/workflow/requesting-db-policy-exception.mdx
echo 'Converted 1070006273 to src/content/ko/user-manual/workflow/requesting-db-policy-exception.mdx'

mkdir -p src/content/ko/user-manual
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544380204/page.xhtml src/content/ko/user-manual/database-access-control.mdx
echo 'Converted 544380204 to src/content/ko/user-manual/database-access-control.mdx'

mkdir -p src/content/ko/user-manual/database-access-control
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544380222/page.xhtml src/content/ko/user-manual/database-access-control/connecting-with-web-sql-editor.mdx
echo 'Converted 544380222 to src/content/ko/user-manual/database-access-control/connecting-with-web-sql-editor.mdx'

mkdir -p src/content/ko/user-manual/database-access-control
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544380354/page.xhtml src/content/ko/user-manual/database-access-control/setting-default-privilege.mdx
echo 'Converted 544380354 to src/content/ko/user-manual/database-access-control/setting-default-privilege.mdx'

mkdir -p src/content/ko/user-manual/database-access-control
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/559906893/page.xhtml src/content/ko/user-manual/database-access-control/connecting-to-proxy-without-agent.mdx
echo 'Converted 559906893 to src/content/ko/user-manual/database-access-control/connecting-to-proxy-without-agent.mdx'

mkdir -p src/content/ko/user-manual/database-access-control
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/820609510/page.xhtml src/content/ko/user-manual/database-access-control/connecting-via-google-bigquery-oauth-authentication.mdx
echo 'Converted 820609510 to src/content/ko/user-manual/database-access-control/connecting-via-google-bigquery-oauth-authentication.mdx'

mkdir -p src/content/ko/user-manual/database-access-control
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/880181257/page.xhtml src/content/ko/user-manual/database-access-control/connecting-to-custom-data-source.mdx
echo 'Converted 880181257 to src/content/ko/user-manual/database-access-control/connecting-to-custom-data-source.mdx'

mkdir -p src/content/ko/user-manual
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544381369/page.xhtml src/content/ko/user-manual/server-access-control.mdx
echo 'Converted 544381369 to src/content/ko/user-manual/server-access-control.mdx'

mkdir -p src/content/ko/user-manual/server-access-control
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544381383/page.xhtml src/content/ko/user-manual/server-access-control/connecting-to-authorized-servers.mdx
echo 'Converted 544381383 to src/content/ko/user-manual/server-access-control/connecting-to-authorized-servers.mdx'

mkdir -p src/content/ko/user-manual/server-access-control
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544381410/page.xhtml src/content/ko/user-manual/server-access-control/using-web-terminal.mdx
echo 'Converted 544381410 to src/content/ko/user-manual/server-access-control/using-web-terminal.mdx'

mkdir -p src/content/ko/user-manual/server-access-control
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544381477/page.xhtml src/content/ko/user-manual/server-access-control/using-web-sftp.mdx
echo 'Converted 544381477 to src/content/ko/user-manual/server-access-control/using-web-sftp.mdx'

mkdir -p src/content/ko/user-manual
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544384011/page.xhtml src/content/ko/user-manual/kubernetes-access-control.mdx
echo 'Converted 544384011 to src/content/ko/user-manual/kubernetes-access-control.mdx'

mkdir -p src/content/ko/user-manual/kubernetes-access-control
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544384025/page.xhtml src/content/ko/user-manual/kubernetes-access-control/checking-access-permission-list.mdx
echo 'Converted 544384025 to src/content/ko/user-manual/kubernetes-access-control/checking-access-permission-list.mdx'

mkdir -p src/content/ko/user-manual
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/1064829218/page.xhtml src/content/ko/user-manual/web-access-control.mdx
echo 'Converted 1064829218 to src/content/ko/user-manual/web-access-control.mdx'

mkdir -p src/content/ko/user-manual/web-access-control
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/1073709107/page.xhtml src/content/ko/user-manual/web-access-control/installing-root-ca-certificate-and-extension.mdx
echo 'Converted 1073709107 to src/content/ko/user-manual/web-access-control/installing-root-ca-certificate-and-extension.mdx'

mkdir -p src/content/ko/user-manual/web-access-control
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/1064796396/page.xhtml src/content/ko/user-manual/web-access-control/accessing-web-applications-websites.mdx
echo 'Converted 1064796396 to src/content/ko/user-manual/web-access-control/accessing-web-applications-websites.mdx'

mkdir -p src/content/ko/user-manual
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/568950885/page.xhtml src/content/ko/user-manual/preferences.mdx
echo 'Converted 568950885 to src/content/ko/user-manual/preferences.mdx'

mkdir -p src/content/ko/user-manual
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544112828/page.xhtml src/content/ko/user-manual/user-agent.mdx
echo 'Converted 544112828 to src/content/ko/user-manual/user-agent.mdx'

mkdir -p src/content/ko/user-manual
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/852066413/page.xhtml src/content/ko/user-manual/multi-agent.mdx
echo 'Converted 852066413 to src/content/ko/user-manual/multi-agent.mdx'

mkdir -p src/content/ko/user-manual/multi-agent
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/912425276/page.xhtml src/content/ko/user-manual/multi-agent/multi-agent-linux-installation-and-usage-guide.mdx
echo 'Converted 912425276 to src/content/ko/user-manual/multi-agent/multi-agent-linux-installation-and-usage-guide.mdx'

mkdir -p src/content/ko/user-manual/multi-agent
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/912425288/page.xhtml src/content/ko/user-manual/multi-agent/multi-agent-seamless-ssh-usage-guide.mdx
echo 'Converted 912425288 to src/content/ko/user-manual/multi-agent/multi-agent-seamless-ssh-usage-guide.mdx'

mkdir -p src/content/ko/user-manual/multi-agent
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/919240916/page.xhtml src/content/ko/user-manual/multi-agent/multi-agent-3rd-party-tool-support-list-by-os.mdx
echo 'Converted 919240916 to src/content/ko/user-manual/multi-agent/multi-agent-3rd-party-tool-support-list-by-os.mdx'

mkdir -p src/content/ko/.
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544178405/page.xhtml src/content/ko/./administrator-manual.mdx
echo 'Converted 544178405 to src/content/ko/./administrator-manual.mdx'

mkdir -p src/content/ko/administrator-manual
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544080057/page.xhtml src/content/ko/administrator-manual/general.mdx
echo 'Converted 544080057 to src/content/ko/administrator-manual/general.mdx'

mkdir -p src/content/ko/administrator-manual/general
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/543948978/page.xhtml src/content/ko/administrator-manual/general/company-management.mdx
echo 'Converted 543948978 to src/content/ko/administrator-manual/general/company-management.mdx'

mkdir -p src/content/ko/administrator-manual/general/company-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544145591/page.xhtml src/content/ko/administrator-manual/general/company-management/general.mdx
echo 'Converted 544145591 to src/content/ko/administrator-manual/general/company-management/general.mdx'

mkdir -p src/content/ko/administrator-manual/general/company-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544178422/page.xhtml src/content/ko/administrator-manual/general/company-management/security.mdx
echo 'Converted 544178422 to src/content/ko/administrator-manual/general/company-management/security.mdx'

mkdir -p src/content/ko/administrator-manual/general/company-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544112846/page.xhtml src/content/ko/administrator-manual/general/company-management/allowed-zones.mdx
echo 'Converted 544112846 to src/content/ko/administrator-manual/general/company-management/allowed-zones.mdx'

mkdir -p src/content/ko/administrator-manual/general/company-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544243925/page.xhtml src/content/ko/administrator-manual/general/company-management/channels.mdx
echo 'Converted 544243925 to src/content/ko/administrator-manual/general/company-management/channels.mdx'

mkdir -p src/content/ko/administrator-manual/general/company-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/543981760/page.xhtml src/content/ko/administrator-manual/general/company-management/alerts.mdx
echo 'Converted 543981760 to src/content/ko/administrator-manual/general/company-management/alerts.mdx'

mkdir -p src/content/ko/administrator-manual/general/company-management/alerts/new-request
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/793608206/page.xhtml src/content/ko/administrator-manual/general/company-management/alerts/new-request/template-variables-by-request-type.mdx
echo 'Converted 793608206 to src/content/ko/administrator-manual/general/company-management/alerts/new-request/template-variables-by-request-type.mdx'

mkdir -p src/content/ko/administrator-manual/general/company-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544178443/page.xhtml src/content/ko/administrator-manual/general/company-management/licenses.mdx
echo 'Converted 544178443 to src/content/ko/administrator-manual/general/company-management/licenses.mdx'

mkdir -p src/content/ko/administrator-manual/general
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544375969/page.xhtml src/content/ko/administrator-manual/general/user-management.mdx
echo 'Converted 544375969 to src/content/ko/administrator-manual/general/user-management.mdx'

mkdir -p src/content/ko/administrator-manual/general/user-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544047331/page.xhtml src/content/ko/administrator-manual/general/user-management/users.mdx
echo 'Converted 544047331 to src/content/ko/administrator-manual/general/user-management/users.mdx'

mkdir -p src/content/ko/administrator-manual/general/user-management/users
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544376787/page.xhtml src/content/ko/administrator-manual/general/user-management/users/user-profile.mdx
echo 'Converted 544376787 to src/content/ko/administrator-manual/general/user-management/users/user-profile.mdx'

mkdir -p src/content/ko/administrator-manual/general/user-management/users
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/920944732/page.xhtml src/content/ko/administrator-manual/general/user-management/users/password-change-enforcement-and-account-deletion-feature-for-qp-admin-default-account.mdx
echo 'Converted 920944732 to src/content/ko/administrator-manual/general/user-management/users/password-change-enforcement-and-account-deletion-feature-for-qp-admin-default-account.mdx'

mkdir -p src/content/ko/administrator-manual/general/user-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544047341/page.xhtml src/content/ko/administrator-manual/general/user-management/groups.mdx
echo 'Converted 544047341 to src/content/ko/administrator-manual/general/user-management/groups.mdx'

mkdir -p src/content/ko/administrator-manual/general/user-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/543948996/page.xhtml src/content/ko/administrator-manual/general/user-management/roles.mdx
echo 'Converted 543948996 to src/content/ko/administrator-manual/general/user-management/roles.mdx'

mkdir -p src/content/ko/administrator-manual/general/user-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544376982/page.xhtml src/content/ko/administrator-manual/general/user-management/profile-editor.mdx
echo 'Converted 544376982 to src/content/ko/administrator-manual/general/user-management/profile-editor.mdx'

mkdir -p src/content/ko/administrator-manual/general/user-management/profile-editor
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/953221256/page.xhtml src/content/ko/administrator-manual/general/user-management/profile-editor/custom-attribute.mdx
echo 'Converted 953221256 to src/content/ko/administrator-manual/general/user-management/profile-editor/custom-attribute.mdx'

mkdir -p src/content/ko/administrator-manual/general/user-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544375984/page.xhtml src/content/ko/administrator-manual/general/user-management/authentication.mdx
echo 'Converted 544375984 to src/content/ko/administrator-manual/general/user-management/authentication.mdx'

mkdir -p src/content/ko/administrator-manual/general/user-management/authentication
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544376004/page.xhtml src/content/ko/administrator-manual/general/user-management/authentication/integrating-with-ldap.mdx
echo 'Converted 544376004 to src/content/ko/administrator-manual/general/user-management/authentication/integrating-with-ldap.mdx'

mkdir -p src/content/ko/administrator-manual/general/user-management/authentication
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544376100/page.xhtml src/content/ko/administrator-manual/general/user-management/authentication/integrating-with-okta.mdx
echo 'Converted 544376100 to src/content/ko/administrator-manual/general/user-management/authentication/integrating-with-okta.mdx'

mkdir -p src/content/ko/administrator-manual/general/user-management/authentication
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544376183/page.xhtml src/content/ko/administrator-manual/general/user-management/authentication/integrating-with-aws-sso.mdx
echo 'Converted 544376183 to src/content/ko/administrator-manual/general/user-management/authentication/integrating-with-aws-sso.mdx'

mkdir -p src/content/ko/administrator-manual/general/user-management/authentication
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/619381289/page.xhtml src/content/ko/administrator-manual/general/user-management/authentication/integrating-with-google-saml.mdx
echo 'Converted 619381289 to src/content/ko/administrator-manual/general/user-management/authentication/integrating-with-google-saml.mdx'

mkdir -p src/content/ko/administrator-manual/general/user-management/authentication
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/793575425/page.xhtml src/content/ko/administrator-manual/general/user-management/authentication/setting-up-multi-factor-authentication.mdx
echo 'Converted 793575425 to src/content/ko/administrator-manual/general/user-management/authentication/setting-up-multi-factor-authentication.mdx'

mkdir -p src/content/ko/administrator-manual/general/user-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544376236/page.xhtml src/content/ko/administrator-manual/general/user-management/provisioning.mdx
echo 'Converted 544376236 to src/content/ko/administrator-manual/general/user-management/provisioning.mdx'

mkdir -p src/content/ko/administrator-manual/general/user-management/provisioning
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544376265/page.xhtml src/content/ko/administrator-manual/general/user-management/provisioning/activating-provisioning.mdx
echo 'Converted 544376265 to src/content/ko/administrator-manual/general/user-management/provisioning/activating-provisioning.mdx'

mkdir -p src/content/ko/administrator-manual/general/user-management/provisioning
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544376394/page.xhtml src/content/ko/administrator-manual/general/user-management/provisioning/okta-provisioning-integration-guide.mdx
echo 'Converted 544376394 to src/content/ko/administrator-manual/general/user-management/provisioning/okta-provisioning-integration-guide.mdx'

mkdir -p src/content/ko/administrator-manual/general
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544178462/page.xhtml src/content/ko/administrator-manual/general/workflow-management.mdx
echo 'Converted 544178462 to src/content/ko/administrator-manual/general/workflow-management.mdx'

mkdir -p src/content/ko/administrator-manual/general/workflow-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544047359/page.xhtml src/content/ko/administrator-manual/general/workflow-management/all-requests.mdx
echo 'Converted 544047359 to src/content/ko/administrator-manual/general/workflow-management/all-requests.mdx'

mkdir -p src/content/ko/administrator-manual/general/workflow-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544378513/page.xhtml src/content/ko/administrator-manual/general/workflow-management/approval-rules.mdx
echo 'Converted 544378513 to src/content/ko/administrator-manual/general/workflow-management/approval-rules.mdx'

mkdir -p src/content/ko/administrator-manual/general/workflow-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/561414376/page.xhtml src/content/ko/administrator-manual/general/workflow-management/workflow-configurations.mdx
echo 'Converted 561414376 to src/content/ko/administrator-manual/general/workflow-management/workflow-configurations.mdx'

mkdir -p src/content/ko/administrator-manual/general
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544112865/page.xhtml src/content/ko/administrator-manual/general/system.mdx
echo 'Converted 544112865 to src/content/ko/administrator-manual/general/system.mdx'

mkdir -p src/content/ko/administrator-manual/general/system
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544080097/page.xhtml src/content/ko/administrator-manual/general/system/integrations.mdx
echo 'Converted 544080097 to src/content/ko/administrator-manual/general/system/integrations.mdx'

mkdir -p src/content/ko/administrator-manual/general/system/integrations
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544379393/page.xhtml src/content/ko/administrator-manual/general/system/integrations/integrating-with-syslog.mdx
echo 'Converted 544379393 to src/content/ko/administrator-manual/general/system/integrations/integrating-with-syslog.mdx'

mkdir -p src/content/ko/administrator-manual/general/system/integrations
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/557940795/page.xhtml src/content/ko/administrator-manual/general/system/integrations/integrating-with-splunk.mdx
echo 'Converted 557940795 to src/content/ko/administrator-manual/general/system/integrations/integrating-with-splunk.mdx'

mkdir -p src/content/ko/administrator-manual/general/system/integrations
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544379587/page.xhtml src/content/ko/administrator-manual/general/system/integrations/integrating-with-secret-store.mdx
echo 'Converted 544379587 to src/content/ko/administrator-manual/general/system/integrations/integrating-with-secret-store.mdx'

mkdir -p src/content/ko/administrator-manual/general/system/integrations
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/798064641/page.xhtml src/content/ko/administrator-manual/general/system/integrations/integrating-with-email.mdx
echo 'Converted 798064641 to src/content/ko/administrator-manual/general/system/integrations/integrating-with-email.mdx'

mkdir -p src/content/ko/administrator-manual/general/system/integrations
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/811401365/page.xhtml src/content/ko/administrator-manual/general/system/integrations/integrating-google-cloud-api-for-oauth-20.mdx
echo 'Converted 811401365 to src/content/ko/administrator-manual/general/system/integrations/integrating-google-cloud-api-for-oauth-20.mdx'

mkdir -p src/content/ko/administrator-manual/general/system/integrations
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/883654669/page.xhtml src/content/ko/administrator-manual/general/system/integrations/integrating-with-slack-dm.mdx
echo 'Converted 883654669 to src/content/ko/administrator-manual/general/system/integrations/integrating-with-slack-dm.mdx'

mkdir -p src/content/ko/administrator-manual/general/system/integrations/integrating-with-slack-dm
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544378759/page.xhtml src/content/ko/administrator-manual/general/system/integrations/integrating-with-slack-dm/slack-dm-workflow-notification-types.mdx
echo 'Converted 544378759 to src/content/ko/administrator-manual/general/system/integrations/integrating-with-slack-dm/slack-dm-workflow-notification-types.mdx'

mkdir -p src/content/ko/administrator-manual/general/system
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544377652/page.xhtml src/content/ko/administrator-manual/general/system/api-token.mdx
echo 'Converted 544377652 to src/content/ko/administrator-manual/general/system/api-token.mdx'

mkdir -p src/content/ko/administrator-manual/general/system
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544211220/page.xhtml src/content/ko/administrator-manual/general/system/jobs.mdx
echo 'Converted 544211220 to src/content/ko/administrator-manual/general/system/jobs.mdx'

mkdir -p src/content/ko/administrator-manual
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544047372/page.xhtml src/content/ko/administrator-manual/discovery.mdx
echo 'Converted 544047372 to src/content/ko/administrator-manual/discovery.mdx'

mkdir -p src/content/ko/administrator-manual/discovery
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/543949048/page.xhtml src/content/ko/administrator-manual/discovery/discovery-management.mdx
echo 'Converted 543949048 to src/content/ko/administrator-manual/discovery/discovery-management.mdx'

mkdir -p src/content/ko/administrator-manual/discovery/discovery-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/543981852/page.xhtml src/content/ko/administrator-manual/discovery/discovery-management/dashboard.mdx
echo 'Converted 543981852 to src/content/ko/administrator-manual/discovery/discovery-management/dashboard.mdx'

mkdir -p src/content/ko/administrator-manual/discovery/discovery-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544080127/page.xhtml src/content/ko/administrator-manual/discovery/discovery-management/inventory.mdx
echo 'Converted 544080127 to src/content/ko/administrator-manual/discovery/discovery-management/inventory.mdx'

mkdir -p src/content/ko/administrator-manual/discovery/discovery-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/543949058/page.xhtml src/content/ko/administrator-manual/discovery/discovery-management/discovery-jobs.mdx
echo 'Converted 543949058 to src/content/ko/administrator-manual/discovery/discovery-management/discovery-jobs.mdx'

mkdir -p src/content/ko/administrator-manual/discovery/discovery-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/543981865/page.xhtml src/content/ko/administrator-manual/discovery/discovery-management/discovery-history.mdx
echo 'Converted 543981865 to src/content/ko/administrator-manual/discovery/discovery-management/discovery-history.mdx'

mkdir -p src/content/ko/administrator-manual/discovery/discovery-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/543949078/page.xhtml src/content/ko/administrator-manual/discovery/discovery-management/scan-results.mdx
echo 'Converted 543949078 to src/content/ko/administrator-manual/discovery/discovery-management/scan-results.mdx'

mkdir -p src/content/ko/administrator-manual/discovery/discovery-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544244011/page.xhtml src/content/ko/administrator-manual/discovery/discovery-management/detection-profiles.mdx
echo 'Converted 544244011 to src/content/ko/administrator-manual/discovery/discovery-management/detection-profiles.mdx'

mkdir -p src/content/ko/administrator-manual/discovery/discovery-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544112915/page.xhtml src/content/ko/administrator-manual/discovery/discovery-management/data-patterns.mdx
echo 'Converted 544112915 to src/content/ko/administrator-manual/discovery/discovery-management/data-patterns.mdx'

mkdir -p src/content/ko/administrator-manual
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544379638/page.xhtml src/content/ko/administrator-manual/databases.mdx
echo 'Converted 544379638 to src/content/ko/administrator-manual/databases.mdx'

mkdir -p src/content/ko/administrator-manual/databases
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/956071939/page.xhtml src/content/ko/administrator-manual/databases/dac-general-configurations.mdx
echo 'Converted 956071939 to src/content/ko/administrator-manual/databases/dac-general-configurations.mdx'

mkdir -p src/content/ko/administrator-manual/databases/dac-general-configurations
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/921436219/page.xhtml src/content/ko/administrator-manual/databases/dac-general-configurations/unmasking-zones.mdx
echo 'Converted 921436219 to src/content/ko/administrator-manual/databases/dac-general-configurations/unmasking-zones.mdx'

mkdir -p src/content/ko/administrator-manual/databases
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544379705/page.xhtml src/content/ko/administrator-manual/databases/connection-management.mdx
echo 'Converted 544379705 to src/content/ko/administrator-manual/databases/connection-management.mdx'

mkdir -p src/content/ko/administrator-manual/databases/connection-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544145672/page.xhtml src/content/ko/administrator-manual/databases/connection-management/cloud-providers.mdx
echo 'Converted 544145672 to src/content/ko/administrator-manual/databases/connection-management/cloud-providers.mdx'

mkdir -p src/content/ko/administrator-manual/databases/connection-management/cloud-providers
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544379719/page.xhtml src/content/ko/administrator-manual/databases/connection-management/cloud-providers/synchronizing-db-resources-from-aws.mdx
echo 'Converted 544379719 to src/content/ko/administrator-manual/databases/connection-management/cloud-providers/synchronizing-db-resources-from-aws.mdx'

mkdir -p src/content/ko/administrator-manual/databases/connection-management/cloud-providers
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/562167871/page.xhtml src/content/ko/administrator-manual/databases/connection-management/cloud-providers/synchronizing-db-resources-from-ms-azure.mdx
echo 'Converted 562167871 to src/content/ko/administrator-manual/databases/connection-management/cloud-providers/synchronizing-db-resources-from-ms-azure.mdx'

mkdir -p src/content/ko/administrator-manual/databases/connection-management/cloud-providers
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/562167809/page.xhtml src/content/ko/administrator-manual/databases/connection-management/cloud-providers/synchronizing-db-resources-from-google-cloud.mdx
echo 'Converted 562167809 to src/content/ko/administrator-manual/databases/connection-management/cloud-providers/synchronizing-db-resources-from-google-cloud.mdx'

mkdir -p src/content/ko/administrator-manual/databases/connection-management/cloud-providers
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/712507393/page.xhtml src/content/ko/administrator-manual/databases/connection-management/cloud-providers/verifying-cloud-synchronization-settings-with-dry-run-feature.mdx
echo 'Converted 712507393 to src/content/ko/administrator-manual/databases/connection-management/cloud-providers/verifying-cloud-synchronization-settings-with-dry-run-feature.mdx'

mkdir -p src/content/ko/administrator-manual/databases/connection-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544014712/page.xhtml src/content/ko/administrator-manual/databases/connection-management/db-connections.mdx
echo 'Converted 544014712 to src/content/ko/administrator-manual/databases/connection-management/db-connections.mdx'

mkdir -p src/content/ko/administrator-manual/databases/connection-management/db-connections
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544380381/page.xhtml src/content/ko/administrator-manual/databases/connection-management/db-connections/mongodb-specific-guide.mdx
echo 'Converted 544380381 to src/content/ko/administrator-manual/databases/connection-management/db-connections/mongodb-specific-guide.mdx'

mkdir -p src/content/ko/administrator-manual/databases/connection-management/db-connections
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/568852692/page.xhtml src/content/ko/administrator-manual/databases/connection-management/db-connections/documentdb-specific-guide.mdx
echo 'Converted 568852692 to src/content/ko/administrator-manual/databases/connection-management/db-connections/documentdb-specific-guide.mdx'

mkdir -p src/content/ko/administrator-manual/databases/connection-management/db-connections
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/811434142/page.xhtml src/content/ko/administrator-manual/databases/connection-management/db-connections/google-bigquery-oauth-authentication-configuration.mdx
echo 'Converted 811434142 to src/content/ko/administrator-manual/databases/connection-management/db-connections/google-bigquery-oauth-authentication-configuration.mdx'

mkdir -p src/content/ko/administrator-manual/databases/connection-management/db-connections
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/820806182/page.xhtml src/content/ko/administrator-manual/databases/connection-management/db-connections/aws-athena-specific-guide.mdx
echo 'Converted 820806182 to src/content/ko/administrator-manual/databases/connection-management/db-connections/aws-athena-specific-guide.mdx'

mkdir -p src/content/ko/administrator-manual/databases/connection-management/db-connections
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/880082945/page.xhtml src/content/ko/administrator-manual/databases/connection-management/db-connections/custom-data-source-configuration-and-log-verification.mdx
echo 'Converted 880082945 to src/content/ko/administrator-manual/databases/connection-management/db-connections/custom-data-source-configuration-and-log-verification.mdx'

mkdir -p src/content/ko/administrator-manual/databases/connection-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544145691/page.xhtml src/content/ko/administrator-manual/databases/connection-management/ssl-configurations.mdx
echo 'Converted 544145691 to src/content/ko/administrator-manual/databases/connection-management/ssl-configurations.mdx'

mkdir -p src/content/ko/administrator-manual/databases/connection-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544047436/page.xhtml src/content/ko/administrator-manual/databases/connection-management/ssh-configurations.mdx
echo 'Converted 544047436 to src/content/ko/administrator-manual/databases/connection-management/ssh-configurations.mdx'

mkdir -p src/content/ko/administrator-manual/databases/connection-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544112932/page.xhtml src/content/ko/administrator-manual/databases/connection-management/kerberos-configurations.mdx
echo 'Converted 544112932 to src/content/ko/administrator-manual/databases/connection-management/kerberos-configurations.mdx'

mkdir -p src/content/ko/administrator-manual/databases
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544380126/page.xhtml src/content/ko/administrator-manual/databases/db-access-control.mdx
echo 'Converted 544380126 to src/content/ko/administrator-manual/databases/db-access-control.mdx'

mkdir -p src/content/ko/administrator-manual/databases/db-access-control
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544380140/page.xhtml src/content/ko/administrator-manual/databases/db-access-control/privilege-type.mdx
echo 'Converted 544380140 to src/content/ko/administrator-manual/databases/db-access-control/privilege-type.mdx'

mkdir -p src/content/ko/administrator-manual/databases/db-access-control
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544380173/page.xhtml src/content/ko/administrator-manual/databases/db-access-control/access-control.mdx
echo 'Converted 544380173 to src/content/ko/administrator-manual/databases/db-access-control/access-control.mdx'

mkdir -p src/content/ko/administrator-manual/databases
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544379868/page.xhtml src/content/ko/administrator-manual/databases/policies.mdx
echo 'Converted 544379868 to src/content/ko/administrator-manual/databases/policies.mdx'

mkdir -p src/content/ko/administrator-manual/databases/policies
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544379937/page.xhtml src/content/ko/administrator-manual/databases/policies/data-access.mdx
echo 'Converted 544379937 to src/content/ko/administrator-manual/databases/policies/data-access.mdx'

mkdir -p src/content/ko/administrator-manual/databases/policies
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/569376769/page.xhtml src/content/ko/administrator-manual/databases/policies/masking-pattern.mdx
echo 'Converted 569376769 to src/content/ko/administrator-manual/databases/policies/masking-pattern.mdx'

mkdir -p src/content/ko/administrator-manual/databases/policies
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544379882/page.xhtml src/content/ko/administrator-manual/databases/policies/data-masking.mdx
echo 'Converted 544379882 to src/content/ko/administrator-manual/databases/policies/data-masking.mdx'

mkdir -p src/content/ko/administrator-manual/databases/policies
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544379993/page.xhtml src/content/ko/administrator-manual/databases/policies/sensitive-data.mdx
echo 'Converted 544379993 to src/content/ko/administrator-manual/databases/policies/sensitive-data.mdx'

mkdir -p src/content/ko/administrator-manual/databases/policies
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/713129986/page.xhtml src/content/ko/administrator-manual/databases/policies/policy-exception.mdx
echo 'Converted 713129986 to src/content/ko/administrator-manual/databases/policies/policy-exception.mdx'

mkdir -p src/content/ko/administrator-manual/databases
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/571277577/page.xhtml src/content/ko/administrator-manual/databases/ledger-management.mdx
echo 'Converted 571277577 to src/content/ko/administrator-manual/databases/ledger-management.mdx'

mkdir -p src/content/ko/administrator-manual/databases/ledger-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544380061/page.xhtml src/content/ko/administrator-manual/databases/ledger-management/ledger-table-policy.mdx
echo 'Converted 544380061 to src/content/ko/administrator-manual/databases/ledger-management/ledger-table-policy.mdx'

mkdir -p src/content/ko/administrator-manual/databases/ledger-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/571277650/page.xhtml src/content/ko/administrator-manual/databases/ledger-management/ledger-approval-rules.mdx
echo 'Converted 571277650 to src/content/ko/administrator-manual/databases/ledger-management/ledger-approval-rules.mdx'

mkdir -p src/content/ko/administrator-manual/databases
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/873136365/page.xhtml src/content/ko/administrator-manual/databases/new-policy-management.mdx
echo 'Converted 873136365 to src/content/ko/administrator-manual/databases/new-policy-management.mdx'

mkdir -p src/content/ko/administrator-manual/databases/new-policy-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/878805502/page.xhtml src/content/ko/administrator-manual/databases/new-policy-management/data-paths.mdx
echo 'Converted 878805502 to src/content/ko/administrator-manual/databases/new-policy-management/data-paths.mdx'

mkdir -p src/content/ko/administrator-manual/databases/new-policy-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/879198569/page.xhtml src/content/ko/administrator-manual/databases/new-policy-management/data-policies.mdx
echo 'Converted 879198569 to src/content/ko/administrator-manual/databases/new-policy-management/data-policies.mdx'

mkdir -p src/content/ko/administrator-manual/databases/new-policy-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/1064796485/page.xhtml src/content/ko/administrator-manual/databases/new-policy-management/exception-management.mdx
echo 'Converted 1064796485 to src/content/ko/administrator-manual/databases/new-policy-management/exception-management.mdx'

mkdir -p src/content/ko/administrator-manual/databases
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/954139156/page.xhtml src/content/ko/administrator-manual/databases/monitoring.mdx
echo 'Converted 954139156 to src/content/ko/administrator-manual/databases/monitoring.mdx'

mkdir -p src/content/ko/administrator-manual/databases/monitoring
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/954172219/page.xhtml src/content/ko/administrator-manual/databases/monitoring/runnig-queries.mdx
echo 'Converted 954172219 to src/content/ko/administrator-manual/databases/monitoring/runnig-queries.mdx'

mkdir -p src/content/ko/administrator-manual/databases/monitoring
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/954204974/page.xhtml src/content/ko/administrator-manual/databases/monitoring/proxy-management.mdx
echo 'Converted 954204974 to src/content/ko/administrator-manual/databases/monitoring/proxy-management.mdx'

mkdir -p src/content/ko/administrator-manual
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544380588/page.xhtml src/content/ko/administrator-manual/servers.mdx
echo 'Converted 544380588 to src/content/ko/administrator-manual/servers.mdx'

mkdir -p src/content/ko/administrator-manual/servers
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/954336174/page.xhtml src/content/ko/administrator-manual/servers/sac-general-configurations.mdx
echo 'Converted 954336174 to src/content/ko/administrator-manual/servers/sac-general-configurations.mdx'

mkdir -p src/content/ko/administrator-manual/servers
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544380635/page.xhtml src/content/ko/administrator-manual/servers/connection-management.mdx
echo 'Converted 544380635 to src/content/ko/administrator-manual/servers/connection-management.mdx'

mkdir -p src/content/ko/administrator-manual/servers/connection-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544178567/page.xhtml src/content/ko/administrator-manual/servers/connection-management/cloud-providers.mdx
echo 'Converted 544178567 to src/content/ko/administrator-manual/servers/connection-management/cloud-providers.mdx'

mkdir -p src/content/ko/administrator-manual/servers/connection-management/cloud-providers
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544380650/page.xhtml src/content/ko/administrator-manual/servers/connection-management/cloud-providers/synchronizing-server-resources-from-aws.mdx
echo 'Converted 544380650 to src/content/ko/administrator-manual/servers/connection-management/cloud-providers/synchronizing-server-resources-from-aws.mdx'

mkdir -p src/content/ko/administrator-manual/servers/connection-management/cloud-providers
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544380741/page.xhtml src/content/ko/administrator-manual/servers/connection-management/cloud-providers/synchronizing-server-resources-from-azure.mdx
echo 'Converted 544380741 to src/content/ko/administrator-manual/servers/connection-management/cloud-providers/synchronizing-server-resources-from-azure.mdx'

mkdir -p src/content/ko/administrator-manual/servers/connection-management/cloud-providers
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544380708/page.xhtml src/content/ko/administrator-manual/servers/connection-management/cloud-providers/synchronizing-server-resources-from-gcp.mdx
echo 'Converted 544380708 to src/content/ko/administrator-manual/servers/connection-management/cloud-providers/synchronizing-server-resources-from-gcp.mdx'

mkdir -p src/content/ko/administrator-manual/servers/connection-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544211361/page.xhtml src/content/ko/administrator-manual/servers/connection-management/servers.mdx
echo 'Converted 544211361 to src/content/ko/administrator-manual/servers/connection-management/servers.mdx'

mkdir -p src/content/ko/administrator-manual/servers/connection-management/servers
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544380774/page.xhtml src/content/ko/administrator-manual/servers/connection-management/servers/manually-registering-individual-servers.mdx
echo 'Converted 544380774 to src/content/ko/administrator-manual/servers/connection-management/servers/manually-registering-individual-servers.mdx'

mkdir -p src/content/ko/administrator-manual/servers/connection-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544080186/page.xhtml src/content/ko/administrator-manual/servers/connection-management/server-groups.mdx
echo 'Converted 544080186 to src/content/ko/administrator-manual/servers/connection-management/server-groups.mdx'

mkdir -p src/content/ko/administrator-manual/servers/connection-management/server-groups
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544380846/page.xhtml src/content/ko/administrator-manual/servers/connection-management/server-groups/managing-servers-as-groups.mdx
echo 'Converted 544380846 to src/content/ko/administrator-manual/servers/connection-management/server-groups/managing-servers-as-groups.mdx'

mkdir -p src/content/ko/administrator-manual/servers/connection-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544211376/page.xhtml src/content/ko/administrator-manual/servers/connection-management/server-agents-for-rdp.mdx
echo 'Converted 544211376 to src/content/ko/administrator-manual/servers/connection-management/server-agents-for-rdp.mdx'

mkdir -p src/content/ko/administrator-manual/servers/connection-management/server-agents-for-rdp
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/565575990/page.xhtml src/content/ko/administrator-manual/servers/connection-management/server-agents-for-rdp/installing-and-removing-server-agent.mdx
echo 'Converted 565575990 to src/content/ko/administrator-manual/servers/connection-management/server-agents-for-rdp/installing-and-removing-server-agent.mdx'

mkdir -p src/content/ko/administrator-manual/servers/connection-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/615710737/page.xhtml src/content/ko/administrator-manual/servers/connection-management/proxyjump-configurations.mdx
echo 'Converted 615710737 to src/content/ko/administrator-manual/servers/connection-management/proxyjump-configurations.mdx'

mkdir -p src/content/ko/administrator-manual/servers/connection-management/proxyjump-configurations
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/615743551/page.xhtml src/content/ko/administrator-manual/servers/connection-management/proxyjump-configurations/creating-proxyjump.mdx
echo 'Converted 615743551 to src/content/ko/administrator-manual/servers/connection-management/proxyjump-configurations/creating-proxyjump.mdx'

mkdir -p src/content/ko/administrator-manual/servers
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/613777446/page.xhtml src/content/ko/administrator-manual/servers/server-account-management.mdx
echo 'Converted 613777446 to src/content/ko/administrator-manual/servers/server-account-management.mdx'

mkdir -p src/content/ko/administrator-manual/servers/server-account-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544380991/page.xhtml src/content/ko/administrator-manual/servers/server-account-management/server-account-templates.mdx
echo 'Converted 544380991 to src/content/ko/administrator-manual/servers/server-account-management/server-account-templates.mdx'

mkdir -p src/content/ko/administrator-manual/servers/server-account-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544380960/page.xhtml src/content/ko/administrator-manual/servers/server-account-management/ssh-key-configurations.mdx
echo 'Converted 544380960 to src/content/ko/administrator-manual/servers/server-account-management/ssh-key-configurations.mdx'

mkdir -p src/content/ko/administrator-manual/servers/server-account-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/615743501/page.xhtml src/content/ko/administrator-manual/servers/server-account-management/account-management.mdx
echo 'Converted 615743501 to src/content/ko/administrator-manual/servers/server-account-management/account-management.mdx'

mkdir -p src/content/ko/administrator-manual/servers/server-account-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/615677962/page.xhtml src/content/ko/administrator-manual/servers/server-account-management/password-provisioning.mdx
echo 'Converted 615677962 to src/content/ko/administrator-manual/servers/server-account-management/password-provisioning.mdx'

mkdir -p src/content/ko/administrator-manual/servers/server-account-management/password-provisioning
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/619380898/page.xhtml src/content/ko/administrator-manual/servers/server-account-management/password-provisioning/creating-password-change-job.mdx
echo 'Converted 619380898 to src/content/ko/administrator-manual/servers/server-account-management/password-provisioning/creating-password-change-job.mdx'

mkdir -p src/content/ko/administrator-manual/servers
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/543949216/page.xhtml src/content/ko/administrator-manual/servers/server-access-control.mdx
echo 'Converted 543949216 to src/content/ko/administrator-manual/servers/server-access-control.mdx'

mkdir -p src/content/ko/administrator-manual/servers/server-access-control
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544381186/page.xhtml src/content/ko/administrator-manual/servers/server-access-control/access-control.mdx
echo 'Converted 544381186 to src/content/ko/administrator-manual/servers/server-access-control/access-control.mdx'

mkdir -p src/content/ko/administrator-manual/servers/server-access-control/access-control
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544381282/page.xhtml src/content/ko/administrator-manual/servers/server-access-control/access-control/granting-and-revoking-permissions.mdx
echo 'Converted 544381282 to src/content/ko/administrator-manual/servers/server-access-control/access-control/granting-and-revoking-permissions.mdx'

mkdir -p src/content/ko/administrator-manual/servers/server-access-control/access-control
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544381200/page.xhtml src/content/ko/administrator-manual/servers/server-access-control/access-control/granting-and-revoking-roles.mdx
echo 'Converted 544381200 to src/content/ko/administrator-manual/servers/server-access-control/access-control/granting-and-revoking-roles.mdx'

mkdir -p src/content/ko/administrator-manual/servers/server-access-control/access-control
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/878838349/page.xhtml src/content/ko/administrator-manual/servers/server-access-control/access-control/granting-server-privilege.mdx
echo 'Converted 878838349 to src/content/ko/administrator-manual/servers/server-access-control/access-control/granting-server-privilege.mdx'

mkdir -p src/content/ko/administrator-manual/servers/server-access-control
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544381150/page.xhtml src/content/ko/administrator-manual/servers/server-access-control/roles.mdx
echo 'Converted 544381150 to src/content/ko/administrator-manual/servers/server-access-control/roles.mdx'

mkdir -p src/content/ko/administrator-manual/servers/server-access-control
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544381025/page.xhtml src/content/ko/administrator-manual/servers/server-access-control/policies.mdx
echo 'Converted 544381025 to src/content/ko/administrator-manual/servers/server-access-control/policies.mdx'

mkdir -p src/content/ko/administrator-manual/servers/server-access-control/policies
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544381039/page.xhtml src/content/ko/administrator-manual/servers/server-access-control/policies/setting-server-access-policy.mdx
echo 'Converted 544381039 to src/content/ko/administrator-manual/servers/server-access-control/policies/setting-server-access-policy.mdx'

mkdir -p src/content/ko/administrator-manual/servers/server-access-control/policies
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544377895/page.xhtml src/content/ko/administrator-manual/servers/server-access-control/policies/enabling-server-proxy.mdx
echo 'Converted 544377895 to src/content/ko/administrator-manual/servers/server-access-control/policies/enabling-server-proxy.mdx'

mkdir -p src/content/ko/administrator-manual/servers/server-access-control
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544381118/page.xhtml src/content/ko/administrator-manual/servers/server-access-control/command-templates.mdx
echo 'Converted 544381118 to src/content/ko/administrator-manual/servers/server-access-control/command-templates.mdx'

mkdir -p src/content/ko/administrator-manual/servers/server-access-control
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544244109/page.xhtml src/content/ko/administrator-manual/servers/server-access-control/blocked-accounts.mdx
echo 'Converted 544244109 to src/content/ko/administrator-manual/servers/server-access-control/blocked-accounts.mdx'

mkdir -p src/content/ko/administrator-manual
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544381596/page.xhtml src/content/ko/administrator-manual/kubernetes.mdx
echo 'Converted 544381596 to src/content/ko/administrator-manual/kubernetes.mdx'

mkdir -p src/content/ko/administrator-manual/kubernetes
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/954172232/page.xhtml src/content/ko/administrator-manual/kubernetes/kac-general-configurations.mdx
echo 'Converted 954172232 to src/content/ko/administrator-manual/kubernetes/kac-general-configurations.mdx'

mkdir -p src/content/ko/administrator-manual/kubernetes
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544381637/page.xhtml src/content/ko/administrator-manual/kubernetes/connection-management.mdx
echo 'Converted 544381637 to src/content/ko/administrator-manual/kubernetes/connection-management.mdx'

mkdir -p src/content/ko/administrator-manual/kubernetes/connection-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544381651/page.xhtml src/content/ko/administrator-manual/kubernetes/connection-management/cloud-providers.mdx
echo 'Converted 544381651 to src/content/ko/administrator-manual/kubernetes/connection-management/cloud-providers.mdx'

mkdir -p src/content/ko/administrator-manual/kubernetes/connection-management/cloud-providers
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544381739/page.xhtml src/content/ko/administrator-manual/kubernetes/connection-management/cloud-providers/synchronizing-kubernetes-resources-from-aws.mdx
echo 'Converted 544381739 to src/content/ko/administrator-manual/kubernetes/connection-management/cloud-providers/synchronizing-kubernetes-resources-from-aws.mdx'

mkdir -p src/content/ko/administrator-manual/kubernetes/connection-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544381839/page.xhtml src/content/ko/administrator-manual/kubernetes/connection-management/clusters.mdx
echo 'Converted 544381839 to src/content/ko/administrator-manual/kubernetes/connection-management/clusters.mdx'

mkdir -p src/content/ko/administrator-manual/kubernetes/connection-management/clusters
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544381877/page.xhtml src/content/ko/administrator-manual/kubernetes/connection-management/clusters/manually-registering-kubernetes-clusters.mdx
echo 'Converted 544381877 to src/content/ko/administrator-manual/kubernetes/connection-management/clusters/manually-registering-kubernetes-clusters.mdx'

mkdir -p src/content/ko/administrator-manual/kubernetes
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544383110/page.xhtml src/content/ko/administrator-manual/kubernetes/k8s-access-control.mdx
echo 'Converted 544383110 to src/content/ko/administrator-manual/kubernetes/k8s-access-control.mdx'

mkdir -p src/content/ko/administrator-manual/kubernetes/k8s-access-control
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544383124/page.xhtml src/content/ko/administrator-manual/kubernetes/k8s-access-control/access-control.mdx
echo 'Converted 544383124 to src/content/ko/administrator-manual/kubernetes/k8s-access-control/access-control.mdx'

mkdir -p src/content/ko/administrator-manual/kubernetes/k8s-access-control/access-control
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544383381/page.xhtml src/content/ko/administrator-manual/kubernetes/k8s-access-control/access-control/granting-and-revoking-kubernetes-roles.mdx
echo 'Converted 544383381 to src/content/ko/administrator-manual/kubernetes/k8s-access-control/access-control/granting-and-revoking-kubernetes-roles.mdx'

mkdir -p src/content/ko/administrator-manual/kubernetes/k8s-access-control
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544382741/page.xhtml src/content/ko/administrator-manual/kubernetes/k8s-access-control/roles.mdx
echo 'Converted 544382741 to src/content/ko/administrator-manual/kubernetes/k8s-access-control/roles.mdx'

mkdir -p src/content/ko/administrator-manual/kubernetes/k8s-access-control/roles
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544382963/page.xhtml src/content/ko/administrator-manual/kubernetes/k8s-access-control/roles/setting-kubernetes-roles.mdx
echo 'Converted 544382963 to src/content/ko/administrator-manual/kubernetes/k8s-access-control/roles/setting-kubernetes-roles.mdx'

mkdir -p src/content/ko/administrator-manual/kubernetes/k8s-access-control
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544382060/page.xhtml src/content/ko/administrator-manual/kubernetes/k8s-access-control/policies.mdx
echo 'Converted 544382060 to src/content/ko/administrator-manual/kubernetes/k8s-access-control/policies.mdx'

mkdir -p src/content/ko/administrator-manual/kubernetes/k8s-access-control/policies
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544382274/page.xhtml src/content/ko/administrator-manual/kubernetes/k8s-access-control/policies/setting-kubernetes-policies.mdx
echo 'Converted 544382274 to src/content/ko/administrator-manual/kubernetes/k8s-access-control/policies/setting-kubernetes-policies.mdx'

mkdir -p src/content/ko/administrator-manual/kubernetes/k8s-access-control/policies
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544382364/page.xhtml src/content/ko/administrator-manual/kubernetes/k8s-access-control/policies/kubernetes-policy-yaml-code-syntax-guide.mdx
echo 'Converted 544382364 to src/content/ko/administrator-manual/kubernetes/k8s-access-control/policies/kubernetes-policy-yaml-code-syntax-guide.mdx'

mkdir -p src/content/ko/administrator-manual/kubernetes/k8s-access-control/policies
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544382445/page.xhtml src/content/ko/administrator-manual/kubernetes/k8s-access-control/policies/kubernetes-policy-tips-guide.mdx
echo 'Converted 544382445 to src/content/ko/administrator-manual/kubernetes/k8s-access-control/policies/kubernetes-policy-tips-guide.mdx'

mkdir -p src/content/ko/administrator-manual/kubernetes/k8s-access-control/policies
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544382522/page.xhtml src/content/ko/administrator-manual/kubernetes/k8s-access-control/policies/kubernetes-policy-ui-code-helper-guide.mdx
echo 'Converted 544382522 to src/content/ko/administrator-manual/kubernetes/k8s-access-control/policies/kubernetes-policy-ui-code-helper-guide.mdx'

mkdir -p src/content/ko/administrator-manual/kubernetes/k8s-access-control/policies
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544382659/page.xhtml src/content/ko/administrator-manual/kubernetes/k8s-access-control/policies/kubernetes-policy-action-configuration-reference-guide.mdx
echo 'Converted 544382659 to src/content/ko/administrator-manual/kubernetes/k8s-access-control/policies/kubernetes-policy-action-configuration-reference-guide.mdx'

mkdir -p src/content/ko/administrator-manual
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/783515900/page.xhtml src/content/ko/administrator-manual/web-apps.mdx
echo 'Converted 783515900 to src/content/ko/administrator-manual/web-apps.mdx'

mkdir -p src/content/ko/administrator-manual/web-apps
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/1064829276/page.xhtml src/content/ko/administrator-manual/web-apps/connection-management.mdx
echo 'Converted 1064829276 to src/content/ko/administrator-manual/web-apps/connection-management.mdx'

mkdir -p src/content/ko/administrator-manual/web-apps/connection-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/1070694423/page.xhtml src/content/ko/administrator-manual/web-apps/connection-management/web-apps.mdx
echo 'Converted 1070694423 to src/content/ko/administrator-manual/web-apps/connection-management/web-apps.mdx'

mkdir -p src/content/ko/administrator-manual/web-apps/connection-management
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/1064829246/page.xhtml src/content/ko/administrator-manual/web-apps/connection-management/web-app-configurations.mdx
echo 'Converted 1064829246 to src/content/ko/administrator-manual/web-apps/connection-management/web-app-configurations.mdx'

mkdir -p src/content/ko/administrator-manual/web-apps
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/1070596135/page.xhtml src/content/ko/administrator-manual/web-apps/web-app-access-control.mdx
echo 'Converted 1070596135 to src/content/ko/administrator-manual/web-apps/web-app-access-control.mdx'

mkdir -p src/content/ko/administrator-manual/web-apps/web-app-access-control
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/1070628904/page.xhtml src/content/ko/administrator-manual/web-apps/web-app-access-control/access-control.mdx
echo 'Converted 1070628904 to src/content/ko/administrator-manual/web-apps/web-app-access-control/access-control.mdx'

mkdir -p src/content/ko/administrator-manual/web-apps/web-app-access-control/access-control
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/1064599910/page.xhtml src/content/ko/administrator-manual/web-apps/web-app-access-control/access-control/granting-and-revoking-roles.mdx
echo 'Converted 1064599910 to src/content/ko/administrator-manual/web-apps/web-app-access-control/access-control/granting-and-revoking-roles.mdx'

mkdir -p src/content/ko/administrator-manual/web-apps/web-app-access-control
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/1070628923/page.xhtml src/content/ko/administrator-manual/web-apps/web-app-access-control/roles.mdx
echo 'Converted 1070628923 to src/content/ko/administrator-manual/web-apps/web-app-access-control/roles.mdx'

mkdir -p src/content/ko/administrator-manual/web-apps/web-app-access-control
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/1064829343/page.xhtml src/content/ko/administrator-manual/web-apps/web-app-access-control/policies.mdx
echo 'Converted 1064829343 to src/content/ko/administrator-manual/web-apps/web-app-access-control/policies.mdx'

mkdir -p src/content/ko/administrator-manual/web-apps
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/783417593/page.xhtml src/content/ko/administrator-manual/web-apps/wac-quickstart.mdx
echo 'Converted 783417593 to src/content/ko/administrator-manual/web-apps/wac-quickstart.mdx'

mkdir -p src/content/ko/administrator-manual/web-apps/wac-quickstart
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/783745324/page.xhtml src/content/ko/administrator-manual/web-apps/wac-quickstart/1027-wac-role-policy-guide.mdx
echo 'Converted 783745324 to src/content/ko/administrator-manual/web-apps/wac-quickstart/1027-wac-role-policy-guide.mdx'

mkdir -p src/content/ko/administrator-manual/web-apps/wac-quickstart
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/924287097/page.xhtml src/content/ko/administrator-manual/web-apps/wac-quickstart/1028-wac-rbac-guide.mdx
echo 'Converted 924287097 to src/content/ko/administrator-manual/web-apps/wac-quickstart/1028-wac-rbac-guide.mdx'

mkdir -p src/content/ko/administrator-manual/web-apps/wac-quickstart
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/956235931/page.xhtml src/content/ko/administrator-manual/web-apps/wac-quickstart/1030-wac-jit-permission-acquisition-guide.mdx
echo 'Converted 956235931 to src/content/ko/administrator-manual/web-apps/wac-quickstart/1030-wac-jit-permission-acquisition-guide.mdx'

mkdir -p src/content/ko/administrator-manual/web-apps/wac-quickstart
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/805962425/page.xhtml src/content/ko/administrator-manual/web-apps/wac-quickstart/root-ca-certificate-installation-guide.mdx
echo 'Converted 805962425 to src/content/ko/administrator-manual/web-apps/wac-quickstart/root-ca-certificate-installation-guide.mdx'

mkdir -p src/content/ko/administrator-manual/web-apps/wac-quickstart
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/883654785/page.xhtml src/content/ko/administrator-manual/web-apps/wac-quickstart/initial-wac-setup-in-web-app-configurations.mdx
echo 'Converted 883654785 to src/content/ko/administrator-manual/web-apps/wac-quickstart/initial-wac-setup-in-web-app-configurations.mdx'

mkdir -p src/content/ko/administrator-manual/web-apps/wac-quickstart
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/924319936/page.xhtml src/content/ko/administrator-manual/web-apps/wac-quickstart/wac-troubleshooting-guide.mdx
echo 'Converted 924319936 to src/content/ko/administrator-manual/web-apps/wac-quickstart/wac-troubleshooting-guide.mdx'

mkdir -p src/content/ko/administrator-manual/web-apps/wac-quickstart
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/927629410/page.xhtml src/content/ko/administrator-manual/web-apps/wac-quickstart/wac-faq.mdx
echo 'Converted 927629410 to src/content/ko/administrator-manual/web-apps/wac-quickstart/wac-faq.mdx'

mkdir -p src/content/ko/administrator-manual
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544379062/page.xhtml src/content/ko/administrator-manual/audit.mdx
echo 'Converted 544379062 to src/content/ko/administrator-manual/audit.mdx'

mkdir -p src/content/ko/administrator-manual/audit
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/693043522/page.xhtml src/content/ko/administrator-manual/audit/reports.mdx
echo 'Converted 693043522 to src/content/ko/administrator-manual/audit/reports.mdx'

mkdir -p src/content/ko/administrator-manual/audit/reports
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544384417/page.xhtml src/content/ko/administrator-manual/audit/reports/reports.mdx
echo 'Converted 544384417 to src/content/ko/administrator-manual/audit/reports/reports.mdx'

mkdir -p src/content/ko/administrator-manual/audit/reports
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544379140/page.xhtml src/content/ko/administrator-manual/audit/reports/audit-log-export.mdx
echo 'Converted 544379140 to src/content/ko/administrator-manual/audit/reports/audit-log-export.mdx'

mkdir -p src/content/ko/administrator-manual/audit
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544211450/page.xhtml src/content/ko/administrator-manual/audit/general-logs.mdx
echo 'Converted 544211450 to src/content/ko/administrator-manual/audit/general-logs.mdx'

mkdir -p src/content/ko/administrator-manual/audit/general-logs
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544080230/page.xhtml src/content/ko/administrator-manual/audit/general-logs/user-access-history.mdx
echo 'Converted 544080230 to src/content/ko/administrator-manual/audit/general-logs/user-access-history.mdx'

mkdir -p src/content/ko/administrator-manual/audit/general-logs
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544113108/page.xhtml src/content/ko/administrator-manual/audit/general-logs/activity-logs.mdx
echo 'Converted 544113108 to src/content/ko/administrator-manual/audit/general-logs/activity-logs.mdx'

mkdir -p src/content/ko/administrator-manual/audit/general-logs
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544047557/page.xhtml src/content/ko/administrator-manual/audit/general-logs/admin-role-history.mdx
echo 'Converted 544047557 to src/content/ko/administrator-manual/audit/general-logs/admin-role-history.mdx'

mkdir -p src/content/ko/administrator-manual/audit/general-logs
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/705724442/page.xhtml src/content/ko/administrator-manual/audit/general-logs/workflow-logs.mdx
echo 'Converted 705724442 to src/content/ko/administrator-manual/audit/general-logs/workflow-logs.mdx'

mkdir -p src/content/ko/administrator-manual/audit/general-logs
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/775455036/page.xhtml src/content/ko/administrator-manual/audit/general-logs/reverse-tunnels.mdx
echo 'Converted 775455036 to src/content/ko/administrator-manual/audit/general-logs/reverse-tunnels.mdx'

mkdir -p src/content/ko/administrator-manual/audit/general-logs/reverse-tunnels
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/811434216/page.xhtml src/content/ko/administrator-manual/audit/general-logs/reverse-tunnels/communicating-with-servers-through-reverse-tunnel.mdx
echo 'Converted 811434216 to src/content/ko/administrator-manual/audit/general-logs/reverse-tunnels/communicating-with-servers-through-reverse-tunnel.mdx'

mkdir -p src/content/ko/administrator-manual/audit/general-logs/reverse-tunnels
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/811466988/page.xhtml src/content/ko/administrator-manual/audit/general-logs/reverse-tunnels/communicating-with-clusters-through-reverse-tunnel.mdx
echo 'Converted 811466988 to src/content/ko/administrator-manual/audit/general-logs/reverse-tunnels/communicating-with-clusters-through-reverse-tunnel.mdx'

mkdir -p src/content/ko/administrator-manual/audit/general-logs/reverse-tunnels
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/955318273/page.xhtml src/content/ko/administrator-manual/audit/general-logs/reverse-tunnels/communicating-with-db-through-reverse-tunnel.mdx
echo 'Converted 955318273 to src/content/ko/administrator-manual/audit/general-logs/reverse-tunnels/communicating-with-db-through-reverse-tunnel.mdx'

mkdir -p src/content/ko/administrator-manual/audit
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544080248/page.xhtml src/content/ko/administrator-manual/audit/database-logs.mdx
echo 'Converted 544080248 to src/content/ko/administrator-manual/audit/database-logs.mdx'

mkdir -p src/content/ko/administrator-manual/audit/database-logs
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544113141/page.xhtml src/content/ko/administrator-manual/audit/database-logs/db-access-history.mdx
echo 'Converted 544113141 to src/content/ko/administrator-manual/audit/database-logs/db-access-history.mdx'

mkdir -p src/content/ko/administrator-manual/audit/database-logs
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544244149/page.xhtml src/content/ko/administrator-manual/audit/database-logs/query-audit.mdx
echo 'Converted 544244149 to src/content/ko/administrator-manual/audit/database-logs/query-audit.mdx'

mkdir -p src/content/ko/administrator-manual/audit/database-logs
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544145819/page.xhtml src/content/ko/administrator-manual/audit/database-logs/running-queries.mdx
echo 'Converted 544145819 to src/content/ko/administrator-manual/audit/database-logs/running-queries.mdx'

mkdir -p src/content/ko/administrator-manual/audit/database-logs
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544244163/page.xhtml src/content/ko/administrator-manual/audit/database-logs/dml-snapshots.mdx
echo 'Converted 544244163 to src/content/ko/administrator-manual/audit/database-logs/dml-snapshots.mdx'

mkdir -p src/content/ko/administrator-manual/audit/database-logs
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544014894/page.xhtml src/content/ko/administrator-manual/audit/database-logs/account-lock-history.mdx
echo 'Converted 544014894 to src/content/ko/administrator-manual/audit/database-logs/account-lock-history.mdx'

mkdir -p src/content/ko/administrator-manual/audit/database-logs
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544080264/page.xhtml src/content/ko/administrator-manual/audit/database-logs/access-control-logs.mdx
echo 'Converted 544080264 to src/content/ko/administrator-manual/audit/database-logs/access-control-logs.mdx'

mkdir -p src/content/ko/administrator-manual/audit/database-logs
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/1070694532/page.xhtml src/content/ko/administrator-manual/audit/database-logs/policy-audit-logs.mdx
echo 'Converted 1070694532 to src/content/ko/administrator-manual/audit/database-logs/policy-audit-logs.mdx'

mkdir -p src/content/ko/administrator-manual/audit/database-logs
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/1164705793/page.xhtml src/content/ko/administrator-manual/audit/database-logs/policy-exception-logs.mdx
echo 'Converted 1164705793 to src/content/ko/administrator-manual/audit/database-logs/policy-exception-logs.mdx'

mkdir -p src/content/ko/administrator-manual/audit
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544014907/page.xhtml src/content/ko/administrator-manual/audit/server-logs.mdx
echo 'Converted 544014907 to src/content/ko/administrator-manual/audit/server-logs.mdx'

mkdir -p src/content/ko/administrator-manual/audit/server-logs
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544244182/page.xhtml src/content/ko/administrator-manual/audit/server-logs/server-access-history.mdx
echo 'Converted 544244182 to src/content/ko/administrator-manual/audit/server-logs/server-access-history.mdx'

mkdir -p src/content/ko/administrator-manual/audit/server-logs
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544244208/page.xhtml src/content/ko/administrator-manual/audit/server-logs/command-audit.mdx
echo 'Converted 544244208 to src/content/ko/administrator-manual/audit/server-logs/command-audit.mdx'

mkdir -p src/content/ko/administrator-manual/audit/server-logs
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544014927/page.xhtml src/content/ko/administrator-manual/audit/server-logs/session-logs.mdx
echo 'Converted 544014927 to src/content/ko/administrator-manual/audit/server-logs/session-logs.mdx'

mkdir -p src/content/ko/administrator-manual/audit/server-logs
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544014940/page.xhtml src/content/ko/administrator-manual/audit/server-logs/session-monitoring.mdx
echo 'Converted 544014940 to src/content/ko/administrator-manual/audit/server-logs/session-monitoring.mdx'

mkdir -p src/content/ko/administrator-manual/audit/server-logs
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544244234/page.xhtml src/content/ko/administrator-manual/audit/server-logs/access-control-logs.mdx
echo 'Converted 544244234 to src/content/ko/administrator-manual/audit/server-logs/access-control-logs.mdx'

mkdir -p src/content/ko/administrator-manual/audit/server-logs
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544244244/page.xhtml src/content/ko/administrator-manual/audit/server-logs/server-role-history.mdx
echo 'Converted 544244244 to src/content/ko/administrator-manual/audit/server-logs/server-role-history.mdx'

mkdir -p src/content/ko/administrator-manual/audit/server-logs
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/543949311/page.xhtml src/content/ko/administrator-manual/audit/server-logs/account-lock-history.mdx
echo 'Converted 543949311 to src/content/ko/administrator-manual/audit/server-logs/account-lock-history.mdx'

mkdir -p src/content/ko/administrator-manual/audit
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544383513/page.xhtml src/content/ko/administrator-manual/audit/kubernetes-logs.mdx
echo 'Converted 544383513 to src/content/ko/administrator-manual/audit/kubernetes-logs.mdx'

mkdir -p src/content/ko/administrator-manual/audit/kubernetes-logs
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544383587/page.xhtml src/content/ko/administrator-manual/audit/kubernetes-logs/request-audit.mdx
echo 'Converted 544383587 to src/content/ko/administrator-manual/audit/kubernetes-logs/request-audit.mdx'

mkdir -p src/content/ko/administrator-manual/audit/kubernetes-logs
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544383693/page.xhtml src/content/ko/administrator-manual/audit/kubernetes-logs/pod-session-recordings.mdx
echo 'Converted 544383693 to src/content/ko/administrator-manual/audit/kubernetes-logs/pod-session-recordings.mdx'

mkdir -p src/content/ko/administrator-manual/audit/kubernetes-logs
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/544383799/page.xhtml src/content/ko/administrator-manual/audit/kubernetes-logs/kubernetes-role-history.mdx
echo 'Converted 544383799 to src/content/ko/administrator-manual/audit/kubernetes-logs/kubernetes-role-history.mdx'

mkdir -p src/content/ko/administrator-manual/audit
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/1064829366/page.xhtml src/content/ko/administrator-manual/audit/web-app-logs.mdx
echo 'Converted 1064829366 to src/content/ko/administrator-manual/audit/web-app-logs.mdx'

mkdir -p src/content/ko/administrator-manual/audit/web-app-logs
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/1064829380/page.xhtml src/content/ko/administrator-manual/audit/web-app-logs/web-access-history.mdx
echo 'Converted 1064829380 to src/content/ko/administrator-manual/audit/web-app-logs/web-access-history.mdx'

mkdir -p src/content/ko/administrator-manual/audit/web-app-logs
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/1070563457/page.xhtml src/content/ko/administrator-manual/audit/web-app-logs/web-event-audit.mdx
echo 'Converted 1070563457 to src/content/ko/administrator-manual/audit/web-app-logs/web-event-audit.mdx'

mkdir -p src/content/ko/administrator-manual/audit/web-app-logs
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/1070694561/page.xhtml src/content/ko/administrator-manual/audit/web-app-logs/user-activity-recordings.mdx
echo 'Converted 1070694561 to src/content/ko/administrator-manual/audit/web-app-logs/user-activity-recordings.mdx'

mkdir -p src/content/ko/administrator-manual/audit/web-app-logs
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/1070563469/page.xhtml src/content/ko/administrator-manual/audit/web-app-logs/web-app-role-history.mdx
echo 'Converted 1070563469 to src/content/ko/administrator-manual/audit/web-app-logs/web-app-role-history.mdx'

mkdir -p src/content/ko/administrator-manual/audit/web-app-logs
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/1070694552/page.xhtml src/content/ko/administrator-manual/audit/web-app-logs/jit-access-control-logs.mdx
echo 'Converted 1070694552 to src/content/ko/administrator-manual/audit/web-app-logs/jit-access-control-logs.mdx'

mkdir -p src/content/ko/administrator-manual
python scripts/confluence_xhtml_to_markdown.py docs/latest-ko-confluence/851280543/page.xhtml src/content/ko/administrator-manual/multi-agent-limitations.mdx
echo 'Converted 851280543 to src/content/ko/administrator-manual/multi-agent-limitations.mdx'

