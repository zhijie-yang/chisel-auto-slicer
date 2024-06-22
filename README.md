# The Chisel Auto Slicer

For helping creating [chisel-releases](https://github.com/canonical/chisel-releases/tree/main) slice definition files.

- [x] Automatically generate slice-definition-alike (SDF-alike) files for a given package with just one command.
- [x] Automatically categorise files into `bins`, `config`, `libs`, `data` and `rest`*.
  - *`rest` contains files that are not categorised into any types of files above.
- [x] Automatically detect if a dependent package already has a slice definition file in [chisel-releases](https://github.com/canonical/chisel-releases/tree/main).
- [x] Automatically generate SDF-alike files for dependent packages if they do not have one already in [chisel-releases](https://github.com/canonical/chisel-releases/tree/main)
- [ ] Support multiple Ubuntu releases (currently only supports the same as the host system)
- [ ] Support multiple architectures (currently only supports the same as the host system)

## Getting started

```bash
python3 -m pip install -r requirements.txt
./chisel_auto_slicer.py --help
```

## Usage

### Find the dependencies of a package, e.g. `libpython3.10-stdlib`:
```bash
./chisel_auto_slicer.py libpython3.10-stdlib --depends
```
Outputs:
```python
['libpython3.10-minimal', 'media-types', 'mime-support', 'libbz2-1.0', 'libc6', 'libcrypt1', 'libdb5.3', 'libffi8', 'liblzma5', 'libmpdec3', 'libncursesw6', 'libnsl2', 'libreadline8', 'libsqlite3-0', 'libtinfo6', 'libtirpc3', 'libuuid1']
```

### Find the full dependencies of a package, e.g. `libpython3.10-stdlib`:
```bash
./chisel_auto_slicer.py libpython3.10-stdlib --full-depends
```
Outputs:
```python
['debconf', 'debconf-2.0', 'dpkg', 'gcc-12-base', 'install-info', 'libbz2-1.0', 'libc6', 'libcom-err2', 'libcrypt1', 'libdb5.3', 'libffi8', 'libgcc-s1', 'libgdbm-compat4', 'libgdbm6', 'libgssapi-krb5-2', 'libk5crypto3', 'libkeyutils1', 'libkrb5-3', 'libkrb5support0', 'liblzma5', 'libmpdec3', 'libncursesw6', 'libnsl2', 'libperl5.34', 'libpython3.10-minimal', 'libreadline8', 'libsqlite3-0', 'libssl3', 'libstdc++6', 'libtinfo6', 'libtirpc-common', 'libtirpc3', 'libuuid1', 'mailcap', 'media-types', 'mime-support', 'perl', 'perl-base', 'perl-modules-5.34', 'readline-common', 'tar', 'zlib1g']
```

### Generate a SDF-alike file for a given package, e.g. `openssl`:
```bash
./chisel_auto_slicer.py openssl --slice
```
Outputs:
```yaml
THE SDF-LIKE SLICE DEFINITION FOR openssl:
=====BEGIN=====
package: openssl

essential:
- openssl_copyright

slices:
  copyright:
    contents:
      /usr/share/doc/openssl/copyright -> ../libssl3/copyright:
  config:
    contents:
      /usr/lib/ssl/openssl.cnf -> /etc/ssl/openssl.cnf:
      /etc/ssl/openssl.cnf:
  libs:
    contents:
      /usr/lib/ssl/misc/tsget -> tsget.pl:
      /usr/lib/ssl/certs -> /etc/ssl/certs:
      /usr/lib/ssl/private -> /etc/ssl/private:
      /usr/lib/ssl/misc/CA.pl:
      /usr/lib/ssl/misc/tsget.pl:
    essential:
    - libc6_libs
    - libssl3_libs
  bins:
    contents:
      /usr/bin/openssl:
      /usr/bin/c_rehash:
    essential:
    - libc6_libs
    - libssl3_libs
    - openssl_config
    - openssl_libs

======END======
```

You need to manually verify if the symbolic links in the generated SDF-alike file. Also be aware that there can be extra/missing essential slices listed, and extra/missing slices. This generated SDF-alike files are just a starting point of creating a slice definition files.

### Generate SDF-alike files for a given package and all of its dependencies, e.g. `libpython3.10-stdlib`:
```bash
./chisel_auto_slicer.py libpython3.10-stdlib --slice --full-depends
```

Outputs:
```
THE SDF-LIKE SLICE DEFINITION FOR debconf:
=====BEGIN=====
<yaml SDF-alike file for `debconf`>
======END======
Press ENTER to continue on debconf-2.0, 'q ENTER' to quit: 
Package debconf-2.0 not found
Press ENTER to continue on gcc-12-base, 'q ENTER' to quit: 
THE SDF-LIKE SLICE DEFINITION FOR gcc-12-base:
=====BEGIN=====
<yaml SDF-alike file for `gcc-12-base`>
======END======
Press ENTER to continue on libc6, 'q ENTER' to quit: 
Package libc6 already sliced in chisel-releases for ubuntu-22.04
Package libcrypt1 already sliced in chisel-releases for ubuntu-22.04
Package libgcc-s1 already sliced in chisel-releases for ubuntu-22.04
Package libssl3 already sliced in chisel-releases for ubuntu-22.04
THE SDF-LIKE SLICE DEFINITION FOR openssl:
=====BEGIN=====
<yaml SDF-alike file for `openssl`>
======END======
