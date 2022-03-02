# File: ParentyReport.gpr.py
register(REPORT,
	id='ParentyReport',
	name=_("ParentyReport"),
	description = _("Report for parenty based on a tag"),
	status = STABLE, # not yet tested with python 3
	version = '0.0.1',
	fname="ParentyReport.py",
    authors = ["Eric Doutreleau"],
    authors_email = ["eric@doutreleau.fr"],
    category = CATEGORY_TEXT,
    require_active = False,
    reportclass = 'ParentyReport',
    optionclass = 'ParentyOptions',
    report_modes = [REPORT_MODE_GUI, REPORT_MODE_CLI],
	gramps_target_version = "5.1",
	)
