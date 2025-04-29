#! /usr/bin/env python3
'Download audio only using youtube_dl'

import argparse
import glob
import shutil
import re
import subprocess
import tempfile
import youtube_dl


def _build_rsync_dest_re():
    a = r'([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9])'
    hostname = r'(' + a + r'\.)*' + a
    return re.compile(r'^(' + a + '@|)' + hostname + r':')

_RSYNC_DEST_RE = _build_rsync_dest_re()


def download(url, args):
    '''Download audio

    :param url:   The URL to download
    :param args:  Arguments
    :return:      The downloaded file path
    '''

    if args.skip_if_exist:
        ss = glob.glob(args.workdir + '/source.*')
        if ss:
            return ss[0]

    opts = {
            'format': '140',
            'outtmpl': args.workdir + '/source.%(ext)s',
    }
    with youtube_dl.YoutubeDL(opts) as ydl:
        retcode = ydl.download([url])
        if retcode:
            raise ValueError(f'retcode={retcode}')

    return glob.glob(args.workdir + '/source.*')[0]


def postprocess(src_file, args):
    '''Postprocess the file

    :param src_file:  Source file path
    :param args:      Arguments
    :return:          The converted file path
    '''

    dst_file = args.workdir + '/postprocess.m4a'

    cmd = [
            'ffmpeg',
            '-hide_banner',
            '-i', src_file,
    ]

    if args.mono:
        cmd += [
                '-ac', '1',
        ]
    else:
        cmd += [
                '-c', 'copy',
        ]

    cmd += [
            '-movflags', '+faststart',
            '-y', dst_file,
    ]
    subprocess.run(cmd, cwd=args.workdir, check=True, stdin=subprocess.DEVNULL)

    return dst_file


def rsync(src, dest):
    '''Send files using rsync command

    :param src:  Source file path
    :param dest: Destination path
    '''
    cmd = [
            'rsync',
            '-avP',
            src,
            dest,
    ]
    subprocess.run(cmd, check=True)


def _get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('url', action='store')
    parser.add_argument('dest', action='store', default=None)

    # Working directory
    parser.add_argument('--workdir', action='store', default=None)
    parser.add_argument('--skip-if-exist', action='store_true', default=False)

    # Conversion option
    parser.add_argument('--mono', action='store_true', default=False)

    return parser.parse_args()


def main():
    'Entry point'
    args = _get_args()

    if not args.workdir:
        # pylint: disable=R1732
        workdir_inst = tempfile.TemporaryDirectory()
        args.workdir = workdir_inst.name

    source_name = download(args.url, args)

    result_name = postprocess(source_name, args)

    if _RSYNC_DEST_RE.match(args.dest):
        rsync(result_name, args.dest)
    else:
        shutil.move(result_name, args.dest)


if __name__ == '__main__':
    main()
