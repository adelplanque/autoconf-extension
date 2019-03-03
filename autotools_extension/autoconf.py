from distutils.core import Command
from distutils.errors import DistutilsExecError
import os
import sys
import tarfile
import tempfile




class autoconf(Command):

    description = "Run autoconf"
    user_options = []

    configure_ac_tmpl = """
    %s
    AC_INIT([%s], [%s])
    AC_CONFIG_MACRO_DIR([m4])
    AM_INIT_AUTOMAKE([foreign -Wall -Werror])
    %s
    AC_CONFIG_FILES([Makefile])
    AC_OUTPUT
    """

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def uptodate(self):
        """
        Check if autoconf should be run
        """
        ac_filename = os.path.join("autoconf", "configure.ac")
        if not os.path.exists(ac_filename):
            return False
        filename = os.path.join("autoconf", "configure")
        if not os.path.exists(filename) \
           or os.path.getmtime(ac_filename) > os.path.getmtime(filename):
            return False
        configure_ac = open(ac_filename, 'r').read()
        return configure_ac == self.create_configure_ac()

    def create_configure_ac(self):
        configure_ac = self.distribution.configure_ac
        for name in ('AC_PREREQ', 'AC_INIT', 'AC_CONFIG_MACRO_DIR',
                     'AM_INIT_AUTOMAKE', 'AC_CONFIG_FILES', 'AC_OUTPUT'):
            if name in configure_ac:
                raise DistutilsExecError(
                    "Don't provide `%s` in configure_ac" % name)
        autoconf_version = self.distribution.autoconf_version
        if autoconf_version is not None:
            prereq = "AC_PREREQ([%s])" % autoconf_version
        else:
            prereq = ""
        return self.configure_ac_tmpl % (
            prereq,
            self.distribution.metadata.name or "foo",
            self.distribution.metadata.version or "1",
            configure_ac
        )

    def run(self):
        if self.uptodate():
            print("Nothing to do")
            return
        if not os.path.exists("autoconf"):
            os.makedirs("autoconf")
        if not os.path.exists("autoconf/m4"):
            os.makedirs("autoconf/m4")
        with open(os.path.join("autoconf", "configure.ac"), "w") as outfile:
            outfile.write(self.create_configure_ac())
        with open(os.path.join("autoconf", "Makefile.am"), "w") as outfile:
            outfile.write("print-dist-archives:\n\t@echo '$(DIST_ARCHIVES)'\n")
        res = os.system("cd autoconf; autoreconf -i")
        exit_code = res >> 8
        if exit_code:
            raise DistutilsExecError()


class configure(Command):

    description = "Run configure"

    def initialize_options(self):
        for name, short, descr in self.user_options:
            if name[-1] == '=':
                setattr(self, name[:-1].replace('-', '_'), None)
            else:
                setattr(self, name.replace('-', '_'), 1)

    def finalize_options(self):
        pass

    def uptodate(self):
        """
        Check if configure should be run.
        """
        config_status = os.path.join("autoconf", "config.status")
        if not os.path.exists(config_status):
            return False
        configure = os.path.join("autoconf", "configure")
        return os.path.getmtime(config_status) > os.path.getmtime(configure)

    def run(self):
        self.run_command('autoconf')
        if self.uptodate():
            print("Nothing to do")
            return

        toks = ['./configure']
        options = self.distribution.get_option_dict(self.__class__.__name__)
        for name, value in options.items():
            toks.append('--%s=%s' % (name.replace('_', '-'), value[1]))
        cmd = "export PYTHON=%s; cd autoconf; " % sys.executable \
            + " ".join(toks)
        print("Configure: %s" % cmd)
        res = os.system(cmd)
        exit_code = res >> 8
        if exit_code:
            raise DistutilsExecError()


import distutils.command.build_ext
distutils_build_ext = distutils.command.build_ext.build_ext


class build_ext(distutils_build_ext):

    def run(self):
        self.run_command('configure')
        distutils_build_ext.run(self)

    def get_autoconf_var(self, name):
        tmp = tempfile.mktemp()
        try:
            with open(tmp + '.in', 'w') as outfile:
                outfile.write(name)
            cmd = os.path.join("autoconf", 'config.status')
            os.system("%s --file=%s" % (cmd, tmp))
            var = open(tmp, 'r').read().strip()
            if var == name:
                print("WARNING: %s not found" % name)
                var = ""
        except:
            try:
                os.remove(tmp + '.in')
            except:
                pass
            try:
                os.remove(tmp)
            except:
                pass
            raise
        return var

    def get_libraries(self, ext):
        libraries = []
        for lib in distutils_build_ext.get_libraries(self, ext):
            if lib[0] == '@' and lib[-1] == '@':
                var = self.get_autoconf_var(lib)
                for tok in var.split():
                    if tok.startswith('-l'):
                        libraries.append(tok[2:])
                    elif tok.startswith('-L'):
                        pass
                    else:
                        libraries.append(tok)
            else:
                libraries.append(lib)
        return libraries

    def get_dirs_prefix(self, dirs, prefix):
        """
        Substitute autoconf variables in directory list.
        """
        new_dirs = []
        for d in dirs:
            if d[0] == '@' and d[-1] == '@':
                var = self.get_autoconf_var(d)
                for tok in var.split():
                    if var.startswith(prefix):
                        new_dirs.append(var[2:])
            else:
                new_dirs.append(d)
        return new_dirs

    def build_extension(self, ext):
        """
        Substitute autoconf variables before build extension.
        """
        ext.library_dirs = self.get_dirs_prefix(ext.library_dirs, '-L')
        ext.include_dirs = self.get_dirs_prefix(ext.include_dirs, '-I')
        distutils_build_ext.build_extension(self, ext)

distutils.command.build_ext.build_ext = build_ext


# Override sdist command to include configure script in source distribution
import distutils.command.sdist
distutils_sdist = distutils.command.sdist.sdist


class sdist(distutils.command.sdist.sdist):

    def make_release_tree(self, base_dir, files):
        """
        Append configure script to source distribution.
        """
        distutils_sdist.make_release_tree(self, base_dir, files)
        os.system("cd autoconf; make dist")
        tmp = tempfile.mktemp()
        try:
            os.system("cd autoconf; make print-dist-archives > %s" % tmp)
            archive = os.path.join("autoconf", open(tmp, 'r').read().strip())
        finally:
            try:
                os.remove(tmp)
            except:
                pass
        dest_dir = os.path.join(base_dir, "autoconf")
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        tar = tarfile.open(archive, 'r')
        for member in tar:
            member.name = '/'.join(member.name.split('/')[1:])
            tar.extract(member, path=dest_dir)
        try:
            os.remove(archive)
        except:
            pass

    sub_commands = [
        ('configure', lambda self: True)
    ] + distutils.command.sdist.sdist.sub_commands

distutils.command.sdist.sdist = sdist


import distutils.dist

distutils_distribution = distutils.dist.Distribution


class Distribution(distutils_distribution):

    def __init__(self, attrs=None):
        self.configure_ac = None
        self.autoconf_version = None
        configure.user_options = attrs.pop('configure_options') or []
        distutils_distribution.__init__(self, attrs)
        self.cmdclass['autoconf'] = autoconf
        self.cmdclass['configure'] = configure
