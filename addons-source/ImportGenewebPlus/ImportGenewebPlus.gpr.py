register(IMPORT,
         id    = 'Import Geneanet format gwplus',
         name  = _('Import Geneanet format gwplus'),
         description =  _('Import gwplus from geneanet'),
         version = '0.0.6',
         gramps_target_version = "5.2",
         status = STABLE,
         fname = 'ImportGenewebPlus.py',
         import_function = 'importData',
         extension = "gwplus"
         )

