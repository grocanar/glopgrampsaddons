#-------------------------------------------------------------------------
#
# register_report
#
#-------------------------------------------------------------------------
register(EXPORT,
  id    = 'ExportParenty',
  name  = _("ExportParenty"),
  description =  _("Export Parenty"),
  version = '1.0.2',
  gramps_target_version = "5.2",
  status = STABLE,
  fname = 'ExportParenty.py',
  authors = ["Eric Doutreleau"],
  authors_email = ["eric@doutreleau.fr"],
  export_function = 'export_data',
  export_options = 'ParentyOptionBox',
  export_options_title = _('Export Parenty File'),
  extension = "pf",

)
