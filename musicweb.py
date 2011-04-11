#!/usr/bin/env python
import re
import os
import glob
import shutil
from jinja2 import Template
import mediafile
import transcode

encodings = ['320', 'V0', 'V2', 'Q8', 'AAC']
album_template = Template(open('album.html').read())
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
        self.dirname = slugify(os.path.split(path)[-1])
        self.path = os.path.join(albums_dir, self.dirname)
        if not os.path.isdir(self.path):
            shutil.copytree(path, self.path)

            # slugify filenames
            for filename in os.listdir(self.path):
                name, extension = os.path.splitext(filename)
                shutil.move(os.path.join(self.path, filename), os.path.join(self.path, slugify(name) + extension))

        self.songs = []
        for song_filename in glob.glob(os.path.join(self.path, "*.flac")):
            self.songs.append(Song(song_filename))

        self.images = []
        for image in glob.glob(os.path.join(self.path, "*.jpg")):
            self.images.append(image)

        self.logs = []
        for log in glob.glob(os.path.join(self.path, "*.log")):
            self.logs.append(log)

        self.cuesheets = []
        for cuesheet in glob.glob(os.path.join(self.path, "*.cue")):
            self.cuesheets.append(cuesheet)

        self.formats = self.transcode()

    def __str__(self):
        return self.songs[0].metadata.album

    def transcode(self):
        formats = []
        for encoding in encodings:
            transcode_dir = os.path.join(self.path, slugify(encoding))
            if not os.path.isdir(transcode_dir):
                os.makedirs(transcode_dir)
            formats.append(transcode.transcode(self.path, encoding, output_dir=transcode_dir))
        return formats
        
class Song:
    def __init__(self, path):
        self.path = path
        self.metadata = mediafile.MediaFile(path)

    def __str__(self):
        return self.metadata.title

def is_album(path):
    extensions = set(os.path.splitext(filename)[-1] for filename in os.listdir(path))
    return ".flac" in extensions

def generate_albums(albums, output_dir):
    pass

def generate_index(albums, output):
    pass

def main():
    music_dir = os.path.expanduser("~/Music")
    output_dir = os.path.expanduser("~/www/music")
    index = os.path.join(output_dir, "index.html")

    albums = []
    for directory in os.listdir(music_dir):
        path = os.path.join(music_dir, directory)
        if is_album(path):
            albums.append(Album(path, output_dir))
    
    generate_albums(albums, output_dir)
    generate_index(albums, index)

if __name__ == "__main__":
    main()
