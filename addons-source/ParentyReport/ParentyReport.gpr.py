# File: ParentyReport.gpr.py
register(REPORT,
	id='ParentyReport',
	name=_("ParentyReport"),
	description = _("Report for parenty based on a tag"),
	status = STABLE, # not yet tested with python 3
<<<<<<< HEAD
	version = '10.4.2',
=======
	version = '10.4.3',
>>>>>>> a64f97d49698b0e632e5a486446674f623b12c66
	fname="ParentyReport.py",
    authors = ["Eric Doutreleau"],
    authors_email = ["eric@doutreleau.fr"],
    category = CATEGORY_TEXT,
    require_active = False,
    reportclass = 'ParentyReport',
    optionclass = 'ParentyOptions',
    report_modes = [REPORT_MODE_GUI, REPORT_MODE_CLI],
	gramps_target_version = "5.2",
	)
