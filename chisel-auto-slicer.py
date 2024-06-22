#!/usr/bin/env python3
import argparse
from collections import OrderedDict
import lsb_release
import os
import subprocess
import sys
from tempfile import TemporaryDirectory as tempdir
import yaml

import apt
import apt.debfile
import git

DOC_DIRS = ["/usr/share/doc", "/usr/share/man"]
LINT_DIRS = ["/usr/share/lintian"]
CONF_DIRS = ["/etc"]
CONF_SUFFICES = [
    ".conf",
    ".cfg",
    ".config",
    ".ini",
    ".json",
    ".xml",
    ".yaml",
    ".yml",
    ".cnf",
]
DATA_DIRS = [
    "/usr/share",
    "/usr/local/share",
    "/var/lib",
    "/var/local/lib",
    "/var/local/share",
    "/var/lib",
    "/var/share",
    "/var/local/share",
    "/var/local/lib",
]
LIBS_DIRS = [
    "/lib",
    "/lib32",
    "/lib64",
    "/usr/lib",
    "/usr/lib32",
    "/usr/lib64",
    "/usr/local/lib",
    "/usr/local/lib32",
    "/usr/local/lib64",
]
BIN_DIRS = [
    "/bin",
    "/sbin",
    "/usr/bin",
    "/usr/sbin",
    "/usr/local/bin",
    "/usr/local/sbin",
]
FILTER_DIRS = DOC_DIRS + LINT_DIRS
FILE_TYPES = {
    "config": (CONF_DIRS, CONF_SUFFICES),
    "data": (DATA_DIRS, []),
    "libs": (LIBS_DIRS, []),
    "bins": (BIN_DIRS, []),
}
INTERDEPENDENT_DEFAULT = {
    "package": ["copyright"],
    "libs": ["depends_libs"],
    "bins": ["libs", "config", "depends_libs"],
}

cache = apt.Cache()
temp_dir = tempdir()


class TopLevelEmptyLineDumper(yaml.Dumper):
    def write_line_break(self, data=None):
        super().write_line_break(data)
        if len(self.indents) == 1:
            super().write_line_break()


def find_depends(pkg_name):
    pkg = cache.get(pkg_name)
    if pkg is None:
        print(f"Package {pkg_name} not found")
        return []
    pkg = pkg.candidate
    return [
        dep.name for base_dep in pkg.get_dependencies("Depends") for dep in base_dep
    ]


def find_full_depends(pkg_name):
    all_deps = set()

    def _do_find_full_depends(pkg_name):
        nonlocal all_deps
        deps = find_depends(pkg_name)
        for dep in deps:
            if dep not in all_deps:
                all_deps.add(dep)
                _do_find_full_depends(dep)

    _do_find_full_depends(pkg_name)
    return sorted(all_deps)


def fetch_pkg(pkg_name) -> os.PathLike:
    pkg = cache.get(pkg_name)
    if pkg is None:
        print(f"Package {pkg_name} not found")
        return
    pkg: apt.Version = pkg.candidate
    return pkg.fetch_binary(temp_dir.name)


def get_dpkg_file_list(pkg_path: os.PathLike) -> list:
    result = subprocess.run(
        ["dpkg", "-c", pkg_path], capture_output=True, text=True, check=True
    )
    file_list = result.stdout.splitlines()
    return file_list


def split_dpkg_file_list(files: list[str]):
    split_files = [file.split() for file in files]
    return [tuple([file[0], *file[5:]]) for file in split_files]


def filter_dpkg_file_list(files: list[list[str]]):
    # filter out directories
    files = [file for file in files if not "d" in file[0]]
    # filter out documents
    for doc_dir in FILTER_DIRS:
        files = [
            file for file in files if not doc_dir in file[1] or "copyright" in file[1]
        ]
    files = [tuple(file[1:]) for file in files]
    return sorted(files, key=lambda x: x[0])


def get_file_by_type(files: list[tuple[str]], dirs: list[str], suffices: list[str]):
    file_set = set()
    if not suffices:
        for dir in dirs:
            file_set.update([file for file in files if dir in file[0]])
        rest_files = [file for file in files if file not in file_set]
    else:
        for dir in dirs:
            for suffix in suffices:
                file_set.update(
                    [
                        file
                        for file in files
                        if dir in file[0] or file[0].endswith(suffix)
                    ]
                )
        rest_files = [file for file in files if file not in file_set]
    return file_set, rest_files


def get_copyright_files(files: list[tuple[str]]):
    file_set = set()
    file_set.update([file for file in files if "copyright" in file[0]])
    rest_files = [file for file in files if file not in file_set]
    return file_set, rest_files


def pretty_print_files(
    files: list[tuple[str]], keep_symbol=False, keep_dst=False, newline_after=True
):
    if keep_symbol and not keep_dst:
        files = sorted([file[0] for file in files])
    elif keep_dst and not keep_symbol:
        files = sorted([file[-1] for file in files])
    elif not keep_symbol and not keep_dst:
        files = sorted([" ".join(file) for file in files])
    else:
        sys.stderr.write("Invalid combination of keep_symbol and keep_dst")
    for file in files:
        print(file)
    if newline_after:
        print()


def get_file_list_tokens(pkg_name: str):
    pkg_path = fetch_pkg(pkg_name)
    if pkg_path is None:
        return
    files = get_dpkg_file_list(pkg_path)
    files = split_dpkg_file_list(files)
    return files


def parse_file_list(files: list[tuple[str]]) -> OrderedDict[str, list[tuple[str]]]:
    slices = OrderedDict(
        {"copyright": [], "config": [], "data": [], "lib": [], "bin": [], "rest": []}
    )
    files, rest = get_copyright_files(files)
    slices["copyright"] = files
    for file_type, (dirs, suffices) in FILE_TYPES.items():
        files, rest = get_file_by_type(rest, dirs, suffices)
        slices[file_type] = files
    slices["rest"] = rest
    return slices


def get_file_tokens_for_pkg(pkg_name):
    files = get_file_list_tokens(pkg_name)
    if files is None:
        return
    files = filter_dpkg_file_list(files)
    files = parse_file_list(files)
    return files


def print_slice_files(pkg_name, files):
    files = filter_dpkg_file_list(files)
    print(f"Slicing files for package {pkg_name}\n")
    print("COPYRIGHT FILES:")
    files, rest = get_copyright_files(files)
    pretty_print_files(files)

    # print files other than copyright
    for file_type, (dirs, suffices) in FILE_TYPES.items():
        files, rest = get_file_by_type(rest, dirs, suffices)
        print(f"{file_type.upper()} FILES:")
        pretty_print_files(files)

    print("REST FILES:")
    pretty_print_files(rest)

    return files


def get_default_essential_slices(pkg_name: str, interdeps: list[str]) -> list[str]:
    """Returns the default essential slices for a given slice

    Args:
        pkg_name (str): the package name
        interdeps (list[str]): the list of interdependent slices

    Returns:
        list[str]: the list of essential slices
    """
    essential = []
    for dep in interdeps:
        # fill in the essential directive for the dependencies from other slices
        if dep.startswith("depends_"):
            slice_name = dep.lstrip("depends_")
            for dep_pkg in find_depends(pkg_name):
                if get_file_tokens_for_pkg(dep_pkg)[slice_name]:
                    essential.append(f"{dep_pkg}_{slice_name}")
        else:  # fill in the essential directive for the dependencies from the same slice
            essential.append(f"{pkg_name}_{dep}")

    return sorted(essential)


def print_sdf_like_files(pkg_name, slices):
    if slices is None:
        return
    slices = {
        k: {"contents": {" ".join(f).lstrip("."): None for f in v}}
        for k, v in slices.items()
    }
    slices = {k: v for k, v in slices.items() if v["contents"]}

    # Add default slices `essential` to slices
    for slice, deps in INTERDEPENDENT_DEFAULT.items():
        if slice in slices:
            slices[slice]["essential"] = get_default_essential_slices(pkg_name, deps)

    sdf = OrderedDict([("package", pkg_name)])

    # Add copyright as package `essential``
    if "copyright" in slices:
        sdf["essential"] = [f"{pkg_name}_copyright"]

    sdf["slices"] = slices

    def represent_none(self, _):
        return self.represent_scalar("tag:yaml.org,2002:null", "")

    yaml.add_representer(type(None), represent_none)
    yaml.add_representer(
        OrderedDict,
        lambda dumper, data: dumper.represent_mapping(
            "tag:yaml.org,2002:map", data.items()
        ),
    )
    print(f"THE SDF-LIKE SLICE DEFINITION FOR {pkg_name}:")
    print("=====BEGIN=====")
    print(yaml.dump(sdf, Dumper=TopLevelEmptyLineDumper, sort_keys=False))
    print("======END======")


def get_chisel_releases_pkgs(ubuntu_release=None) -> lsb_release:
    if ubuntu_release is None:
        ubuntu_release = f"ubuntu-{lsb_release.get_distro_information()['RELEASE']}"

    repo_path = os.path.join(temp_dir.name, "chisel-releases")
    repo = git.Repo.clone_from(
        "https://github.com/canonical/chisel-releases", repo_path
    )
    repo.git.checkout(ubuntu_release)

    pkgs = [
        file.rstrip(".yaml")
        for file in os.listdir(os.path.join(repo_path, "slices"))
        if file.endswith(".yaml")
    ]

    return pkgs


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("package", help="Package name to slice")
    parser.add_argument(
        "--depends", action="store_true", default=False, help="Print all dependencies"
    )
    parser.add_argument(
        "--full-depends",
        action="store_true",
        default=False,
        help="Print the full dependencies",
    )
    parser.add_argument(
        "--slice", action="store_true", default=False, help="Slice the files"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        default=False,
        help="Ignore existing slices in chisel-releases",
    )
    args = parser.parse_args()

    if args.depends and not args.full_depends:
        deps = find_depends(args.package)
        print(deps)

    elif args.full_depends and not args.depends:
        deps = find_full_depends(args.package)
        print(deps)
    elif not args.depends and not args.full_depends:
        deps = []
    else:
        print("Invalid combination of --depends and --deep-depends")
        sys.exit(1)
    deps.append(args.package)

    chisel_releases_pkgs = get_chisel_releases_pkgs()
    ubuntu_release = f"ubuntu-{lsb_release.get_distro_information()['RELEASE']}"

    if args.slice:
        for i, pkg in enumerate(deps):
            if not args.all and pkg in chisel_releases_pkgs:
                print(
                    f"Package {pkg} already sliced in chisel-releases for {ubuntu_release}"
                )
                continue
            files = get_file_tokens_for_pkg(pkg)
            # print(files)
            print_sdf_like_files(pkg, files)
            if len(deps) > 1:
                if i == len(deps) - 1:
                    break
                key = input(
                    f"Press ENTER to continue on {deps[i+1]}, 'q ENTER' to quit: "
                )
                if key == "":
                    continue
                if key == "q":
                    break
                print("Invalid input")
                break
