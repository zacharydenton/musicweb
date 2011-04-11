#!/usr/bin/env python
import re
import os
import glob
import shutil
import fnmatch
import subprocess
from jinja2 import Template
import mediafile
import transcode

encodings = ['FLAC', '320', 'V0', 'V2', 'Q8', 'AAC']
album_template = Template(open('album.html').read())
format_template = Template(open('format.html').read())
index_template = Template(open('index.html').read())

_slugify_strip_re = re.compile(r'[^\w\s-]')
_slugify_hyphenate_re = re.compile(r'[-\s]+')
def slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    
    From Django's "django/template/defaultfilters.py".
    """
    import unicodedata
    if not isinstance(value, unicode):
        value = unicode(value)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = unicode(_slugify_strip_re.sub('', value).strip().lower())
    return _slugify_hyphenate_re.sub('-', value)

class Album:
    def __init__(self, path, albums_dir):
        self.original_path = path
        self.dirname = slugify(os.path.split(self.original_path)[-1])
        self.path = os.path.join(albums_dir, self.dirname)

        self.songs = []
        for song_filename in glob.glob(os.path.join(self.original_path, "*.flac")):
            self.songs.append(Song(song_filename, "FLAC"))
        self.songs.sort(key = lambda s: s.track)

        # copy non-music files
        for filename in os.listdir(self.original_path):
            if not fnmatch.fnmatch(filename, '*.flac'):
                old_file = os.path.join(self.original_path, filename)
                name, ext = os.path.splitext(os.path.basename(old_file))
                new_file = os.path.join(self.path, slugify(name) + ext)
                shutil.copy(old_file, new_file)

        self.title = self.songs[0].album
        self.artists = sorted(set(song.artist for song in self.songs))
        self.genres = sorted(set(song.genre for song in self.songs))
        self.date = self.songs[0].date

        self.images = map(os.path.basename, glob.glob(os.path.join(self.path, "*.jpg")))
        self.logs = map(os.path.basename, glob.glob(os.path.join(self.path, "*.log")))
        self.cuesheets = map(os.path.basename, glob.glob(os.path.join(self.path, "*.cue")))
        self.playlists = map(os.path.basename, glob.glob(os.path.join(self.path, "*.m3u")))

        self.create_formats()

    def __str__(self):
        return self.title

    def create_formats(self):
        self.files = []
        self.formats = []
        self.zips = []
        for encoding in encodings:
            transcode_dir = os.path.join(self.path, slugify(encoding))
            zip_file = os.path.join(self.path, slugify("{title} - {encoding}".format(title=self.title, encoding=encoding)) + ".zip")
            if not os.path.isdir(transcode_dir):
                if encoding == "FLAC":
                    shutil.copytree(self.original_path, transcode_dir)
                else:
                    os.makedirs(transcode_dir)
                    transcode.transcode(self.original_path, encoding, output_dir=transcode_dir)

                # build the zip
                subprocess.call('zip -r "{0}" "{1}"'.format(zip_file, transcode_dir), shell=True)

                # slugify filenames
                for filename in os.listdir(transcode_dir):
                    name, extension = os.path.splitext(filename)
                    shutil.move(os.path.join(transcode_dir, filename), os.path.join(transcode_dir, slugify(name) + extension))

            for filename in glob.glob(os.path.join(transcode_dir, "*")):
                try:
                    self.files.append(Song(filename, encoding=encoding))
                except:
                    pass
            self.formats.append(slugify(encoding))
            self.zips.append((os.path.basename(zip_file), encoding))

    def generate_index(self):
        output = os.path.join(self.path, "index.html")
        content = album_template.render(
            album=self,
        ).encode('utf-8')
        open(output, 'w').write(content)

    def generate_format_pages(self):
        for format in self.formats:
            output = os.path.join(self.path, format, "index.html")
            content = format_template.render(
                title=self.title,
                format=format,
                songs=sorted([song for song in self.files if slugify(song.encoding)==format], key = lambda s: s.track)
            ).encode('utf-8')
            open(output, 'w').write(content)

class Song(mediafile.MediaFile):
    def __init__(self, path, encoding):
        super(Song, self).__init__(path)
        self.encoding = encoding
        self.filename = os.path.basename(path)

    @property
    def encoding_name(self):
        if self.format == self.encoding:
            return self.format
        else:
            return self.format + ' ' + self.encoding
        
def is_album(path):
    extensions = set(os.path.splitext(filename)[-1] for filename in os.listdir(path))
    return ".flac" in extensions

def generate_albums(albums):
    for album in albums:
        album.generate_index()
        album.generate_format_pages()

def generate_index(albums, output):
    albums = sorted(albums, key = lambda a: a.title)
    content = index_template.render(
        albums=albums,
    ).encode('utf-8')
    open(output, 'w').write(content)

def main():
    music_dir = os.path.expanduser("~/Music")
    output_dir = os.path.expanduser("~/www/music")
    index = os.path.join(output_dir, "index.html")

    albums = []
    for directory in os.listdir(music_dir):
        path = os.path.join(music_dir, directory)
        if is_album(path):
            albums.append(Album(path, output_dir))
    
    generate_albums(albums)
    generate_index(albums, index)

if __name__ == "__main__":
    main()
