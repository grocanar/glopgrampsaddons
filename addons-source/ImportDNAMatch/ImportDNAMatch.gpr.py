register(TOOL,
         id    = 'Import DNAMatches',
         name  = _('Import DNAMatches'),
         description =  _('Import DNA match list'),
<<<<<<< HEAD
         version = '0.0.17',
         gramps_target_version = "5.1",
=======
         version = '0.0.18',
         gramps_target_version = "5.2",
>>>>>>> a64f97d49698b0e632e5a486446674f623b12c66
         status = STABLE,
         fname = 'ImportDNAMatch.py',
         authors = ["Eric Doutreleau"],
         authors_email = ["eric@doutreleau.fr"],
         category = TOOL_DBPROC,
         toolclass = 'ImportDNAMatchTool',
         optionclass = 'ImportDNAMatchOptions',
         tool_modes = [TOOL_MODE_GUI],
         )
