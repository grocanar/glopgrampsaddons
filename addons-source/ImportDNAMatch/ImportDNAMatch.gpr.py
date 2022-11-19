register(TOOL,
         id    = 'Import DNAMatches',
         name  = _('Import DNAMatches'),
         description =  _('Import DNA match list'),
         version = '0.0.15',
         gramps_target_version = "5.1",
         status = STABLE,
         fname = 'ImportDNAMatch.py',
         authors = ["Eric Doutreleau"],
         authors_email = ["eric@doutreleau.fr"],
         category = TOOL_DBPROC,
         toolclass = 'ImportDNAMatchTool',
         optionclass = 'ImportDNAMatchOptions',
         tool_modes = [TOOL_MODE_GUI],
         )