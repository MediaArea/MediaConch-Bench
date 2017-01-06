# MediaConch-Bench script

## Summary

The MediaConch bench script can be used to compare size between formats and transcoding time in a multi-thread and sequentially environment.
It reports information about the processus in CSV files than can be compared and interpreted.

The different steps of the process are:

* step 1: Take the source files and transcode them to a specific format.

* step 2: Take the source files and transcode them to another specific format.

* step 3: Analyze the files created in step 2 using MediaConch Implementation.

* step 4: Take files created in step 2 and transcode them to the same format as in step 1.

## Dependency

* Python
* MediaConchd
* ffmpeg
* ffprobe


## Configuration

### JSON

* daemon_path, no default, need to be set, indicates where the MediaConch daemon is.
* ffmpeg_path, default set to "ffmpeg", corresponds to the FFmpeg binary.
* ffprobe_path, default set to "ffprobe", corresponds to the FFprobe binary.
* script_path, no default value, path of the script or binary to use by the confogiration.
* database_dir, default set to on linux:$HOME_DIR/.local/share/Mediaconch, on MacOS:$HOME_DIR/Library/Application Support/MediaConch, on Windows: $HOME_DIR/APPDATA/MediaConch, directory where the MediaConch database is.
* config_dir, default set to on linux:$HOME_DIR/.config, on MacOS:$HOME_DIR/Library/Preferences, on Windows: $HOME_DIR/APPDATA/MediaConch, directory where the MediaConch configuration is.
* log_dir, default set to the local directory, path of the log file to use.
* files_ext, default set to mxf, extentions of the input files.
* files_dir, default set to $files_ext in local directory, directory of the input file.
* created_files_dir, default set local directory, directory where the transcoded files will be created.
* reports_dir, default set to reports in the local directory, where the (CSV) report files will be created.
* nb_core_max, default 2, maximum number of cores to use (Do not use more than the computer have).
* plugins, default no plugins, plugins to use, see below.

### Plugins

The Plugins configuration is the most important part. It indicates the way to use the transcoding parts.
The formatting of the plugins is the same than the one used by MediaConch. Please refere to https://github.com/MediaArea/MediaConch_SourceCode/blob/master/Documentation/Plugins.md for more information about it. You should also use the one provided by default to make your own one.
The name of the plugins needs to be respected in order to be used.

#### ffmpeg1

This plugin is used to transcode file in single thread, sequentially.

* id must be "ffmpeg1".
* outputDir must be tmp1.
* bin will be replaced by the bin configuration variable.

#### ffmpeg1-1

* id must be "ffmpeg1-1".
* outputDir must be tmp1-1.
* bin will be replaced by the bin configuration variable.

#### ffmpeg2

* id must be "ffmpeg2".
* outputDir must be tmp2.
* bin will be replaced by the bin configuration variable.

#### ffmpeg2-1

* id must be "ffmpeg2-1".
* outputDir must be tmp2-1.
* bin will be replaced by the bin configuration variable.

#### ffmpeg4

* id must be "ffmpeg4".
* outputDir must be tmp4.
* bin will be replaced by the bin configuration variable.

#### ffmpeg4-1

* id must be "ffmpeg4-1".
* outputDir must be tmp4-1.
* bin will be replaced by the bin configuration variable.

#### logger

This plugin logs usefull information as timestamp, filename used by the script.
It must be set to use the debug verbose.

* id must be set to "logger".
* level must be set to "all".
* file will be set using the log_dir configuration.

#### Note

In the inputParams of the ffmpeg* plugins, if one of the params is "--ffmpegpath" and followed by at least one param, the next one will be replaced by the ffmpeg_path configuration variable.
In the inputParams of the ffmpeg* plugins, if one of the params is "--ffprobepath" and followed by at least one param, the next one will be replaced by the ffprobe_path configuration variable.

Usage:
* step1: Use ffmpeg1, ffmpeg1-1 and logger.
* step2: Use ffmpeg2, ffmpeg2-1 and logger.
* step3: Use logger.
* step4: Use ffmpeg4, ffmpeg4-1 and logger.

## Run-Time

### Command

If no configuration file is provided, it will use the local config.json file if existing

```shell
python bench.py[ -c config_file.json]
```

### Reports

#### Name

They are created in $reports_dir (report to Configuration part for more details).

Name will be composed with the step number and if using multi-threads or sequencial tests:

$NAME = report-$NUMBER-$TYPE.csv with $NUMBER the step number [1-4] and $TYPE the type of tests [multithreads-sequential]

#### Sequential

Transcode each files one by one sequentially.

The report gives, for each file transcoded, the source file to transcode, its size and its duration, the transcode time and the size of the file created by the transcode.

#### Multi-threads

Transcode files by nb_core_max (see Configuration) in the same times.

The report gives the total transcode time needed.
