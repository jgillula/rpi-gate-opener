dnl configure.ac
dnl
dnl Copyright 2012, 2013 Brandon Invergo <brandon@invergo.net>
dnl
dnl Copying and distribution of this file, with or without modification,
dnl are permitted in any medium without royalty provided the copyright
dnl notice and this notice are preserved.  This file is offered as-is,
dnl without any warranty.

dnl#########
dnl README #
dnl#########
dnl
dnl This is a basic Autoconf configure.ac file for Python-based
dnl projects. It is not intended to be used as-is, but rather to be
dnl modified to the specific needs of the project.
dnl
dnl Lines prefixed with "dnl" are comments that are automatically
dnl removed by Autoconf/M4, thus they will not appear in the generated
dnl configure script (see the M4 documentation for more information). 
dnl Such comments are used in this file to communicate information to 
dnl you, the developer. In some cases, the comments contain extra 
dnl macros that you might consider including in your configure script. 
dnl If you wish to include them, simply remove the "dnl" from the 
dnl beginning of the line.
dnl
dnl Lines prefixed with "#" are comments that will appear in the 
dnl generated configure script. These comments are thus used to clarify
dnl to the user what is happening in that script
dnl
dnl Wherever pyconfigure-specific macros are used, extra comments are
dnl included to describe the macros.

dnl######################
dnl Package Information #
dnl######################

dnl----
dnl Initialize Autoconf with the package metadata
dnl The arguments have been set via the project's PKG-INFO file
dnl and correspond to:
dnl
dnl 1) package name (i.e. foo)
dnl 2) package version (i.e. 1.2)
dnl 3) bug/info/project email address (i.e. bug-foo@gnu.org)
dnl----
dnl
AC_INIT([mqtt-gate-opener], [1.0.0], [jgillula+rpi-gate-opener@gmail.com])

dnl----
dnl Load macros from the m4/ directory. If you plan to write new 
dnl macros, put them in files in this directory.
dnl----
dnl
m4_include([m4/python.m4])

dnl###########################
dnl Program/command support  #
dnl###########################
dnl
dnl In this section, we check for the presence of important commands
dnl and programs.

dnl--PC_INIT----------------------------------------------------------
dnl This is the only required macro. Its primary function is to find
dnl a Python interpreter that is compatible with the package and set 
dnl the PYTHON variable to hold its path. It can optionally take
dnl arguments to specify minimum and/or maximum versions.  This is a 
dnl convenience macro that combines the functionality of the macros
dnl PC_PROG_PYTHON and PC_PYTHON_VERIFY_VERSION
dnl PC_INIT: find an interpreter with a version between 2.0 and 3.3.99
dnl          (in other words, up to and including any possible release
dnl          in the 3.3 series)
dnl PC_INIT([MIN_VER], [MAX_VER]): Find an interpreter that is between
dnl          the minimum and maximum version. If the min is in the 2.0
dnl          series and the max is in the 3.0 series, non-existent 
dnl          releases (2.8 & 2.9) will be correctly skipped.
dnl----
dnl
PC_INIT([3.1], [3.99])

dnl----
dnl With the following set of macros, we implement an option 
dnl "--with-virtualenv", which the user can pass to the configure 
dnl script in order to install to a Virtualenv (AC_ARG_WITH). If the 
dnl option is specified by the user, then we check if the program is
dnl available, checking both for "virtualenv" and "virtualenv2" 
dnl (AC_CHECK_PROGS)
dnl----
dnl
# Support installing to a virtualenv via the --with-virtualenv 
# configure flag
AC_ARG_WITH([virtualenv],
	[AS_HELP_STRING([--with-virtualenv], [install to a Python virtualenv])],
	[],
	[with_virtualenv=no])
AS_IF([test "x$with_virtualenv" != xno],
	    AC_CHECK_PROGS([VIRTUALENV], [virtualenv virtualenv3 virtualenv2], [no])
	    AS_IF([test "x$VIRTUALENV" = xno],
	    [AC_MSG_FAILURE(
		[--with-virtualenv given but virtualenv could not be found])]),
	AC_SUBST([VIRTUALENV], [no]))
AC_ARG_VAR([VIRTUALENV_FLAGS], [flags to pass to the virtualenv command])

dnl----
dnl These are standard Autoconf macros which check for the 
dnl presence of some programs that we will use in the Makefile.
dnl----
dnl
AC_PROG_MKDIR_P
AC_PROG_SED
AC_PROG_INSTALL
AC_PROG_LN_S

dnl###############################
dnl Checking Python capabilities #
dnl###############################

dnl--PC_PYTHON_CHECK_MODULE([PYTHON-MODULE], [ACTION-IF-PRESENT],
dnl                         [ACTION-IF-ABSENT]) 
dnl This macro lets you check if a given Python module exists on the
dnl system.
dnl----
dnl
PC_PYTHON_CHECK_MODULE([time], , AC_MSG_ERROR([Python standard library 'time' could not be found]))
PC_PYTHON_CHECK_MODULE([signal], , AC_MSG_ERROR([Python standard library 'time' could not be found]))
PC_PYTHON_CHECK_MODULE([sys], , AC_MSG_ERROR([Python standard library 'time' could not be found]))
PC_PYTHON_CHECK_MODULE([configparser], , AC_MSG_ERROR([Python standard library 'time' could not be found]))
AS_VAR_SET([missing_python_packages], [""])
PC_PYTHON_CHECK_MODULE([RPi.GPIO], , AS_VAR_APPEND([missing_python_packages], ["RPi.GPIO "]))
PC_PYTHON_CHECK_MODULE([paho.mqtt], , AS_VAR_APPEND([missing_python_packages], ["paho.mqtt "]))
PC_PYTHON_CHECK_MODULE([python-socketio], , AS_VAR_APPEND([missing_python_packages], ["python-socketio "]))
AS_IF([test "$VIRTUALENV" = no -a -n "$missing_python_packages"],
	    AC_MSG_ERROR([The Python packages "$missing_python_packages" are missing and you have not chosen to use a virtual environment. Please either install the missing packages globally or use a virtual environment by running: ./configure --with-virtual-env]))

dnl#########
dnl Finish #
dnl#########

AC_ARG_VAR([SERVICE_USER], [User to run the mqtt-gate-opener service as. Defaults to pi, or root if user pi does not exist.])
AS_IF([test -z "$SERVICE_USER"],
	    AS_IF([id -u pi],
	    	    AS_VAR_SET([SERVICE_USER], [pi]),
		    AS_VAR_SET([SERVICE_USER], [root])))


dnl Define the files to be configured
AC_CONFIG_FILES([Makefile])
dnl Generate the config files
AC_OUTPUT

dnl Print the results to the screen
AS_IF([test "$prefix" = NONE],
	    AC_MSG_NOTICE([Installation will use the prefix "/"]),
	    AC_MSG_NOTICE([Installation will use the prefix "$prefix"]))
AS_IF([test "$VIRTUALENV" != no],
	    AC_MSG_NOTICE([Installation will create a virtual environment and install dependencies there.]))
AC_MSG_NOTICE([The service will run as $SERVICE_USER])
