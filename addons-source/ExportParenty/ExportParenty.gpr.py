#-------------------------------------------------------------------------
#
# register_report
#
#-------------------------------------------------------------------------
register(EXPORT,
  id    = 'ExportParenty',
  name  = _("ExportParenty"),
  description =  _("Export Parenty"),
<<<<<<< HEAD
  version = '1.0.3',
  gramps_target_version = "5.1",
=======
  version = '1.0.4',
  gramps_target_version = "5.2",
>>>>>>> a64f97d49698b0e632e5a486446674f623b12c66
  status = STABLE,
  fname = 'ExportParenty.py',
  authors = ["Eric Doutreleau"],
  authors_email = ["eric@doutreleau.fr"],
  export_function = 'export_data',
  export_options = 'ParentyOptionBox',
  export_options_title = _('Export Parenty File'),
  extension = "pf",

)
