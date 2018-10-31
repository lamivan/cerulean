import logging
from typing import Dict

import pytest
from cerulean import copy
from cerulean.file_system_impl import FileSystemImpl
from cerulean import EntryType, Path, Permission


def assert_dir_copied_correctly(copied_dir: Path) -> None:
    assert copied_dir.exists()
    assert copied_dir.is_dir()
    assert (copied_dir / 'file0').is_file()
    assert (copied_dir / 'file1').is_file()
    assert (copied_dir / 'link0').is_symlink()
    assert (copied_dir / 'link0').readlink().name == 'file0'
    assert (copied_dir / 'link1').is_symlink()
    assert (copied_dir / 'link1').readlink().name == 'link0'
    assert not (copied_dir / 'link2').exists()

    assert (copied_dir / 'link3').is_symlink()
    assert (copied_dir / 'link3').readlink().name == 'link4'
    assert (copied_dir / 'link4').is_symlink()
    assert (copied_dir / 'link4').readlink().name == 'link3'

    assert not (copied_dir / 'fifo').exists()
    assert not (copied_dir / 'chardev').exists()
    assert not (copied_dir / 'blockdev').exists()


def test_copy_file_args(filesystem: FileSystemImpl, paths: Dict[str, Path]) -> None:
    file0 = paths['file']
    with pytest.raises(ValueError):
        copy(file0, file0, overwrite='nonexistentoption')


def test_copy_into(filesystem: FileSystemImpl, paths: Dict[str, Path]) -> None:
    file0 = paths['file']
    newdir = paths['new_dir']
    newdir.mkdir()
    copy(file0, newdir)
    assert (newdir / file0.name).exists()
    newdir.rmdir(recursive=True)


def test_copy_dir_onto_nonexistent(filesystem: FileSystemImpl, paths: Dict[str, Path]) -> None:
    dir0 = paths['dir']
    newdir = paths['new_dir']
    copy(dir0, newdir, overwrite='always', copy_into=False)
    assert newdir.is_dir()
    newdir.rmdir(recursive=True)


def test_copy_file_onto_dir(filesystem: FileSystemImpl, paths: Dict[str, Path]) -> None:
    file1 = paths['file']
    newdir = paths['new_dir']

    newdir.mkdir()
    copy(file1, newdir, overwrite='always', copy_into=False)
    assert newdir.is_file()
    newdir.unlink()


def test_copy_file_single_fs(filesystem: FileSystemImpl, paths: Dict[str, Path]) -> None:
    file1 = paths['file']
    new_file = paths['new_file']

    assert not new_file.exists()
    copy(file1, new_file)
    assert new_file.exists()
    assert new_file.is_file()
    new_file.unlink()

    copy(file1, new_file, overwrite='raise')
    assert new_file.exists()
    new_file.unlink()

    copy(file1, new_file, overwrite='always')
    assert new_file.exists()
    new_file.unlink()

    other_file = paths['other_file']
    copy(file1, other_file)
    assert other_file.size() == 0

    with pytest.raises(FileExistsError):
        copy(file1, other_file, overwrite='raise')

    copy(file1, other_file, overwrite='always')
    assert other_file.size() == 12
    other_file.unlink()
    other_file.touch()


def test_copy_file_permissions(filesystem: FileSystemImpl, paths: Dict[str, Path]) -> None:
    file1 = paths['executable']
    file2 = paths['private']
    new_file = paths['new_file']

    assert file1.has_permission(Permission.OWNER_READ)
    assert file1.has_permission(Permission.OWNER_WRITE)
    assert file1.has_permission(Permission.OWNER_EXECUTE)
    assert file1.has_permission(Permission.GROUP_READ)
    assert not file1.has_permission(Permission.GROUP_WRITE)
    assert not file1.has_permission(Permission.GROUP_EXECUTE)
    assert file1.has_permission(Permission.OTHERS_READ)
    assert not file1.has_permission(Permission.OTHERS_WRITE)
    assert not file1.has_permission(Permission.OTHERS_EXECUTE)
    copy(file1, new_file, copy_permissions=True)
    assert new_file.has_permission(Permission.OWNER_READ)
    assert new_file.has_permission(Permission.OWNER_WRITE)
    assert new_file.has_permission(Permission.OWNER_EXECUTE)
    assert new_file.has_permission(Permission.GROUP_READ)
    assert not new_file.has_permission(Permission.GROUP_WRITE)
    assert not new_file.has_permission(Permission.GROUP_EXECUTE)
    assert new_file.has_permission(Permission.OTHERS_READ)
    assert not new_file.has_permission(Permission.OTHERS_WRITE)
    assert not new_file.has_permission(Permission.OTHERS_EXECUTE)

    new_file.unlink()

    for permission in Permission:
        assert file2.has_permission(permission) == (
                permission in [Permission.OWNER_READ, Permission.OWNER_WRITE])

    copy(file2, new_file, copy_permissions=True)
    for permission in Permission:
        assert file2.has_permission(permission) == (
                permission in [Permission.OWNER_READ, Permission.OWNER_WRITE])

    copy(file1, new_file, overwrite='always', copy_permissions=True)
    assert new_file.has_permission(Permission.OWNER_READ)
    assert new_file.has_permission(Permission.OWNER_WRITE)
    assert new_file.has_permission(Permission.OWNER_EXECUTE)
    assert new_file.has_permission(Permission.GROUP_READ)
    assert not new_file.has_permission(Permission.GROUP_WRITE)
    assert not new_file.has_permission(Permission.GROUP_EXECUTE)
    assert new_file.has_permission(Permission.OTHERS_READ)
    assert not new_file.has_permission(Permission.OTHERS_WRITE)
    assert not new_file.has_permission(Permission.OTHERS_EXECUTE)

    new_file.chmod(0o644)

    copy(file2, new_file, overwrite='always', copy_permissions=True)
    for permission in Permission:
        assert file2.has_permission(permission) == (
                permission in [Permission.OWNER_READ, Permission.OWNER_WRITE])

    new_file.unlink()


def test_no_copy_file_permissions(filesystem: FileSystemImpl, paths: Dict[str, Path]) -> None:
    file1 = paths['executable']
    file2 = paths['private']
    new_file = paths['new_file']

    copy(file1, new_file, copy_permissions=False)
    assert not new_file.has_permission(Permission.OWNER_EXECUTE)

    new_file.unlink()
    new_file.touch()
    new_file.chmod(0o660)
    copy(file1, new_file, overwrite='always', copy_permissions=False)
    assert new_file.has_permission(Permission.OWNER_READ)
    assert new_file.has_permission(Permission.OWNER_WRITE)
    assert not new_file.has_permission(Permission.OWNER_EXECUTE)
    assert not new_file.has_permission(Permission.GROUP_WRITE)
    assert new_file.has_permission(Permission.OTHERS_READ)

    new_file.unlink()
    copy(file2, new_file, overwrite='always', copy_permissions=False)
    for permission in Permission:
        assert file2.has_permission(permission) == (
                permission in [Permission.OWNER_READ, Permission.OWNER_WRITE])

    new_file.unlink()


def test_copy_symlink_single_fs(filesystem: FileSystemImpl, paths: Dict[str, Path]) -> None:
    link = paths['multi_link']
    new_file = paths['new_file']

    assert not new_file.exists()
    copy(link, new_file)

    assert new_file.exists()
    assert new_file.is_file()
    assert new_file.size() == 12

    new_file.unlink()


def test_copy_dir_single_fs(filesystem: FileSystemImpl, paths: Dict[str, Path]) -> None:
    dir1 = paths['dir']
    new_dir = paths['new_dir']

    assert not new_dir.exists()
    copy(dir1, new_dir)

    assert_dir_copied_correctly(new_dir)

    new_dir.rmdir(recursive=True)


def test_copy_dir_single_fs2(filesystem: FileSystemImpl, paths: Dict[str, Path]) -> None:
    dir1 = paths['dir']
    new_dir = paths['new_dir']

    assert not new_dir.exists()
    copy(dir1, new_dir, overwrite='raise')
    assert_dir_copied_correctly(new_dir)

    with pytest.raises(FileExistsError):
        copy(dir1, new_dir, overwrite='raise', copy_into=False)

    new_dir.rmdir(recursive=True)


def test_copy_dir_single_fs3(filesystem: FileSystemImpl, paths: Dict[str, Path]) -> None:
    dir1 = paths['dir']
    new_dir = paths['new_dir']

    assert not new_dir.exists()
    copy(dir1, new_dir)
    assert_dir_copied_correctly(new_dir)

    (new_dir / 'file0').unlink()

    copy(dir1, new_dir, overwrite='always', copy_into=False)
    assert (new_dir / 'file0').exists()

    new_dir.rmdir(recursive=True)

    copy(dir1, new_dir, overwrite='always', copy_into=False)
    assert_dir_copied_correctly(new_dir)

    new_dir.rmdir(recursive=True)

    new_dir.mkdir()
    copy(dir1, new_dir, overwrite='always', copy_into=True)
    assert (new_dir / 'links' / 'file0').exists()

    new_dir.rmdir(recursive=True)


def test_copy_file_cross_fs(filesystem: FileSystemImpl,
                            filesystem2: FileSystemImpl,
                            paths: Dict[str, Path]) -> None:
    file1 = paths['file']
    new_file = filesystem2 / str(paths['new_file'])

    assert not new_file.exists()
    copy(file1, new_file)
    assert new_file.exists()
    assert new_file.is_file()
    new_file.unlink()

    copy(file1, new_file, overwrite='raise')
    assert new_file.exists()
    new_file.unlink()

    copy(file1, new_file, overwrite='always')
    assert new_file.exists()
    new_file.unlink()

    other_file = paths['other_file']
    copy(file1, other_file)
    assert other_file.size() == 0

    with pytest.raises(FileExistsError):
        copy(file1, other_file, overwrite='raise')

    copy(file1, other_file, overwrite='always')
    assert other_file.size() == 12
    other_file.unlink()
    other_file.touch()


def test_copy_symlink_cross_fs(filesystem: FileSystemImpl,
                               filesystem2: FileSystemImpl,
                               paths: Dict[str, Path]) -> None:
    link = paths['multi_link']
    new_file = filesystem2 / str(paths['new_file'])

    assert not new_file.exists()
    copy(link, new_file)

    assert new_file.exists()
    assert new_file.is_file()
    assert new_file.size() == 12

    new_file.unlink()


def test_copy_dir_cross_fs(filesystem: FileSystemImpl,
                           filesystem2: FileSystemImpl,
                           paths: Dict[str, Path]) -> None:
    dir1 = paths['dir']
    new_dir = filesystem2 / str(paths['new_dir'])

    assert not new_dir.exists()
    copy(dir1, new_dir)

    assert_dir_copied_correctly(new_dir)

    new_dir.rmdir(recursive=True)
