
#############################################################################
# treehash.pl by Martin F. Falatic, (c) 2002-2011
#############################################################################
#
# Data hashing tool for archiving and comparison
#
#############################################################################
#
# Required packages (beyond base perl):
#
#   ppm install Win32API-File-Time
#
#############################################################################
#
#	my $hexValList = pack "H*", $hexString;
#	print "Val List : $hexValList\n";
#	my $newHexString = unpack "H*", $hexValList;
#	print "String: \"$newHexString\"\n";
#
#
#	SameFullSameData - O SFSD
#	SameFullDiffData - O SFDD
#
#	SameNameSameData - O SNSD
#	SameNameSameData - S SNSD
#
#	DiffNameSameData - O DNSD
#	DiffNameSameData - S DNSD
#
#
#			#$fileSize = 0xffffffffff; # 1099511627775
#			#$fileSize = 1099511627775; # 0xffffffffff = 1TB - 1
#
#############################################################################
#
# 2002-05-12 v0.01 First version I created
# 2003-01-18 v0.02 Rudimentary batch processing
# 2004-12-27 v1.00 Greatly improved version with command line args and all
# 2005-12-29 v1.10 Overhaul and improvements
# 2009-05-12 v2.03 Minor update
# 2009-06-26 v2.04 Added special mp3 file data-only checksumming
# 2010-04-07 v2.10 Data-only handler for mp3s is working properly now;
#                  tightened the ignored element checks; documented history
#                  more thoroughly
# 2010-10-23 v2.20 Loosened compare strictness for create times and dir mod
#                  times
# 2011-04-05 v2.30 Cleanup for Perl 5.10+
#
#############################################################################
# Included files and global vars
#############################################################################

	#############################################################################
	require 5.010;
	
	use strict;
	use warnings;

	#############################################################################
	my $VERSION    =  2.30;
	my $toolName   = "TreeHash";
	my $toolExec   = "treehash.pl";
	my $toolAuthor = "Martin F. Falatic";
	my $toolCopyrt = "2002-2011";
	my $toolTitle  = "$toolName ".sprintf("%0.2f", $VERSION)." by $toolAuthor, (c) $toolCopyrt";
	
	#############################################################################
	use Cwd;
	use File::Find;
	use File::Path;
	use File::Copy;
	use Data::Dumper;
	use Getopt::Long;
	use Math::BigInt;
	use Win32::File qw(GetAttributes SetAttributes);
    use Win32::API;
	use Win32API::File::Time qw{:win};
	use Compress::Zlib;
	use Algorithm::Diff qw(diff LCS traverse_sequences);

	#############################################################################
	# Unbuffered I/O (new way)
	binmode STDOUT, ':unix';
	binmode STDERR, ':unix';

	#############################################################################
	my $screenWidth = 108;

	my $MAGIC = "MFTH";

   	use constant FILEATTRIB_READONLY            => 0x0001;
	use constant FILEATTRIB_HIDDEN              => 0x0002;
	use constant FILEATTRIB_SYSTEM              => 0x0004;
	use constant FILEATTRIB_RESERVED_0008       => 0x0008;
	use constant FILEATTRIB_DIRECTORY           => 0x0010;
	use constant FILEATTRIB_ARCHIVE             => 0x0020;
	use constant FILEATTRIB_DEVICE              => 0x0040;
	use constant FILEATTRIB_NORMAL              => 0x0080;
	use constant FILEATTRIB_TEMPORARY           => 0x0100;
	use constant FILEATTRIB_SPARSE_FILE         => 0x0200;
	use constant FILEATTRIB_REPARSE_POINT       => 0x0400;
	use constant FILEATTRIB_COMPRESSED          => 0x0800;
	use constant FILEATTRIB_OFFLINE             => 0x1000;
	use constant FILEATTRIB_NOT_CONTENT_INDEXED => 0x2000;
	use constant FILEATTRIB_ENCRYPTED           => 0x4000;
	use constant FILEATTRIB_RESERVED_8000       => 0x8000;
	use constant INVALID_FILEATTRIBS            => 0xFFFF;

	sub Win32AttribsToString {
		my ($attr) = @_;
		my $attrStr;
		my @vect;
		my $i = 0;

		push @vect, (($attr & FILEATTRIB_READONLY)            == FILEATTRIB_READONLY)            ?'R':'-'; $i++;
		push @vect, (($attr & FILEATTRIB_HIDDEN)              == FILEATTRIB_HIDDEN)              ?'H':'-'; $i++;
		push @vect, (($attr & FILEATTRIB_SYSTEM)              == FILEATTRIB_SYSTEM)              ?'S':'-'; $i++;
		push @vect, (($attr & FILEATTRIB_RESERVED_0008)       == FILEATTRIB_RESERVED_0008)       ?'+':'-'; $i++;

		push @vect, (($attr & FILEATTRIB_DIRECTORY)           == FILEATTRIB_DIRECTORY)           ?'D':'-'; $i++;
		push @vect, (($attr & FILEATTRIB_ARCHIVE)             == FILEATTRIB_ARCHIVE)             ?'A':'-'; $i++;
		push @vect, (($attr & FILEATTRIB_DEVICE)              == FILEATTRIB_DEVICE)              ?'v':'-'; $i++;
		push @vect, (($attr & FILEATTRIB_NORMAL)              == FILEATTRIB_NORMAL)              ?'N':'-'; $i++;

		push @vect, (($attr & FILEATTRIB_TEMPORARY)           == FILEATTRIB_TEMPORARY)           ?'t':'-'; $i++;
		push @vect, (($attr & FILEATTRIB_SPARSE_FILE)         == FILEATTRIB_SPARSE_FILE)         ?'s':'-'; $i++;
		push @vect, (($attr & FILEATTRIB_REPARSE_POINT)       == FILEATTRIB_REPARSE_POINT)       ?'r':'-'; $i++;
		push @vect, (($attr & FILEATTRIB_COMPRESSED)          == FILEATTRIB_COMPRESSED)          ?'c':'-'; $i++;

		push @vect, (($attr & FILEATTRIB_OFFLINE)             == FILEATTRIB_OFFLINE)             ?'O':'-'; $i++;
		push @vect, (($attr & FILEATTRIB_NOT_CONTENT_INDEXED) == FILEATTRIB_NOT_CONTENT_INDEXED) ?'i':'-'; $i++;
		push @vect, (($attr & FILEATTRIB_ENCRYPTED)           == FILEATTRIB_ENCRYPTED)           ?'e':'-'; $i++;
		push @vect, (($attr & FILEATTRIB_RESERVED_8000)       == FILEATTRIB_RESERVED_8000)       ?'+':'-'; $i++;

		$attrStr = pack ("a" x $i, @vect);

		return reverse $attrStr;
	}
	
	#############################################################################
	use constant OP_UNDEF   => 0; # Undefined
	use constant OP_SAME    => 1; # No operation required
	use constant OP_MOVE    => 2; # Move element
	use constant OP_COPY    => 3; # Copy element
	use constant OP_UPDATE  => 4; # Update content of element
	use constant OP_CREATE  => 5; # Create new element
	use constant OP_FIXMETA => 6; # Updated metadata ONLY
	use constant OP_REMOVE  => 7; # Remove element

	sub Printable_const_OP {
		my ($constant) = @_;
		my $text;
		if    ($constant == OP_UNDEF)   { $text = "OP_UNDEF";   }
		elsif ($constant == OP_SAME)    { $text = "OP_SAME";    }
		elsif ($constant == OP_MOVE)    { $text = "OP_MOVE";    }
		elsif ($constant == OP_COPY)    { $text = "OP_COPY";    }
		elsif ($constant == OP_UPDATE)  { $text = "OP_UPDATE";  }
		elsif ($constant == OP_CREATE)  { $text = "OP_CREATE";  }
		elsif ($constant == OP_FIXMETA) { $text = "OP_FIXMETA"; }
		elsif ($constant == OP_REMOVE)  { $text = "OP_REMOVE";  }
		return $text;
	}
	
	#############################################################################
	use constant T_NONE => 0; # No type (bad or unspecified)
	use constant T_FILE => 1; # File
	use constant T_DIR  => 2; # Folder
	#use constant T_LINK => 3; # Link (*unsupported*)

	sub Printable_const_T {
		my ($constant) = @_;
		my $text;
		if    ($constant == T_NONE) { $text = "T_NONE"; }
		elsif ($constant == T_FILE) { $text = "T_FILE"; }
		elsif ($constant == T_DIR)  { $text = "T_DIR";  }
		return $text;
	}
	
	#############################################################################
	use constant M_UNDEF => 0; # Undefined (error case)
	use constant M_NONE  => 1; # Diff file Name, Diff Data ("no match" anywhere)
	use constant M_SFSD  => 2; # Same Full name, Same Data (Opposite only)
	use constant M_SFDD  => 3; # Same Full name, Diff Data (Opposite only)
	use constant M_SNSD  => 4; # Same file Name, Same Data (Opposite and Same sides)
	use constant M_DNSD  => 5; # Diff file Name, Same Data (Opposite and Same sides)

	sub Printable_const_M {
		my ($constant) = @_;
		my $text;
		if    ($constant == M_UNDEF) { $text = "_((UNDEFINED!))_"; }
		elsif ($constant == M_NONE)  { $text = "_NO_MATCH_FOUND_"; }
		elsif ($constant == M_SFSD)  { $text = "SameFullSameData"; }
		elsif ($constant == M_SFDD)  { $text = "SameFullDiffData"; }
		elsif ($constant == M_SNSD)  { $text = "SameNameSameData"; }
		elsif ($constant == M_DNSD)  { $text = "DiffNameSameData"; }
		return $text;
	}
	
	#############################################################################

	use constant DEFAULT_FILEIO_CHUNK_SIZE => 0x10000;

	#############################################################################

	my $startTime = time();

	my $DEBUG = 0;
	my $VERBOSE = 0;

	my $MP3_DATA_ONLY = 0; # If ~0, will generate checksum for the mp3 DATA only, excluding headers and tags

	my $BINARY_PRINT = 1; # Used when generating data files

	my $colSep = ";";

	my @ElementList = ();
    my $BytesTotal  = 0;
    my $BytesLocal  = 0;

	my @IgnoredFiles = ( # Files and such we skip (File::Find continues)
		"^".quotemeta("pagefile.sys")."\$",
		"^".quotemeta("hiberfil.sys")."\$",
	);

	my @IgnoredFolders = ( # Folders we skip entirely (causes File::Find to prune)
		"^".quotemeta("\$Recycle.Bin")."\$",
		"^".quotemeta("Recycled")."\$",
		"^".quotemeta("Recycler")."\$",
		"^".quotemeta("System Volume Information")."\$",
		"^".quotemeta("Temp")."\$",
	);

	my $SourcePath  = "";
	my $RestorePath = "";
	my $BackupFile  = "";
	my $CommentString = "";
	my $OutputFilePrefix = "";
	
	my ($PathL, $PathR, $DatfL, $DatfR) = ("","","","");

#############################################################################
# Main program
#############################################################################

	print "\n"."~" x $screenWidth."\n";
	print "*** $toolTitle ***\n\n";

	#########################################################################
	#	Read and validate arguments
	#########################################################################

	my $USAGE_TEXT =
		"\nUsage:\n".
			"    $toolExec -gen     [-alt] [-mp3data] <path1> [<path2>...]\n".
		    "    $toolExec -cmp     <datFile1> <datFile2>\n".
		    "    $toolExec -delta   (-lpath <pathL> | -ldatf <datFileL>) (-rpath <pathR> | -rdatf <datFileR>)\n".
		    "    $toolExec -backup  -file <backupFile> (-lpath <pathL> | -ldatf <datFileL>) (-rpath <pathR> | -rdatf <datFileR>)\n".
		    "    $toolExec -backup  -file <backupFile> (-rpath <pathR> | -rdatf <datFileR>) # All creates\n".
		    "    $toolExec -restore -file <backupFile> -tgtRoot <restoreRoot> [-srcroot <sourceRoot>]\n".
		    " Note: -mp3data processes ONLY audio data (ignores tags) for *.mp3 files\n".
		"\n\n";

	our ($opt_help, $opt_gen, $opt_cmp, $opt_diff, $opt_alt, $opt_delta,
		 $opt_backup, $opt_restore, $opt_debug, $opt_verbose, $opt_mp3data);

	if (!GetOptions("help|?", "gen", "cmp", "diff", "alt", "delta", "backup", "restore", "verbose", "debug", "mp3data",
		"prefix=s", \$OutputFilePrefix, "lpath=s", \$PathL, "rpath=s", \$PathR, "ldatf=s", \$DatfL, "rdatf=s", \$DatfR,
		"file=s", \$BackupFile, "comment=s",  \$CommentString, "srcroot=s", \$SourcePath, "tgtroot=s", \$RestorePath )) {
		print $USAGE_TEXT;
		exit (255);
	}

	if    (defined($opt_help)) {
		print $USAGE_TEXT;
		exit (1);
	}

	if    (defined($opt_mp3data)) {
		print "\n!!! MP3 data mode active (report only checmsum for *audio data* in MP3 files)!!!\n\n";
		$MP3_DATA_ONLY = 1;
	}

	if    (defined($opt_debug)) {
		print "\n!!! DEBUG mode active (max verbosity)!!!\n\n";
		$DEBUG = 1;
		$VERBOSE = 1;
	}
	elsif (defined($opt_verbose)) {
		print "\n!!! VERBOSE mode active !!!\n\n";
		$VERBOSE = 1;
	}

	my (%InfoL, %InfoR, @opList);

	if (defined($opt_delta) || defined($opt_diff) || defined($opt_backup)) {
		if    (($PathL ne "" && $DatfL ne "") || ($PathR ne "" && $DatfR ne "")) {
			print $USAGE_TEXT;
			exit (1);
		}
		elsif ((($PathL eq "" && $DatfL eq "") && !defined($opt_backup)) || ($PathR eq "" && $DatfR eq "")) {
			print $USAGE_TEXT;
			exit (1);
		}

		if    (defined($opt_delta)) {
			RunDelta ($PathL, $DatfL, \%InfoL, $PathR, $DatfR, \%InfoR, \@opList);
		}
		elsif (defined($opt_backup)) {
			RunDelta ($PathL, $DatfL, \%InfoL, $PathR, $DatfR, \%InfoR, \@opList);
			CreateBackup ($BackupFile, $CommentString, \%InfoL, \%InfoR, \@opList);
		}
		elsif (defined($opt_diff)) {
			RunDiff ($PathL, $DatfL, \%InfoL, $PathR, $DatfR, \%InfoR, \@opList);
		}
	}
	elsif (defined($opt_restore)) {
		if    ($BackupFile eq "" || $RestorePath eq "") {
			print $USAGE_TEXT;
			exit (1);
		}

		if ($SourcePath eq "") { # The files will be restored over an existing Restore Path
			$SourcePath = $RestorePath;
		}
		else { # Restore Path is new, create an initial copy of the source path
			system ("cp -rp \"$SourcePath\" \"$RestorePath\""); # Initial restore template creation (basis)
		}

		RestoreBackup ($RestorePath, $BackupFile);
	}
	elsif (defined($opt_gen) && defined($opt_cmp)) {
		print $USAGE_TEXT;
		exit (1);
	}
	elsif (defined($opt_gen) && scalar(@ARGV) > 0) {
		if ($OutputFilePrefix ne "" && scalar(@ARGV) > 1) {
			print "\n!! Cannot use an output file prefix when multipole paths are specified\n\n";
			exit (1);
		}
		GenerateDataFiles($OutputFilePrefix, \@ARGV);
	}
	elsif (defined($opt_cmp) && scalar(@ARGV) == 2) {
		CompareDataFiles(\@ARGV);
	}
	else {
		print $USAGE_TEXT;
		exit (1);
	}

	#########################################################################
	# Exit, as always, *gracefully*!
	#########################################################################

	print "\n"."~" x $screenWidth."\n";
	print ">> Operation complete!\n\n";

	exit 0;

#############################################################################
#############################################################################
#############################################################################
#############################################################################

#############################################################################
#
#############################################################################
sub CompressionTest {
	print "\nZlib test\n\n";

	my ($startPos1, $startPos2, $defSize);

	# Valid values for deflation levels are -1 through 9, with certain defines:
	# -1 = Z_DEFAULT_COMPRESSION
	#  0 = Z_NO_COMPRESSION
	#  1 = Z_BEST_SPEED
	#  ......
	#  9 = Z_BEST_COMPRESSION
	$startPos1 = 12000000;
	$defSize   = Deflatus("foo",   "foo.z", $startPos1, -1);

	$startPos1 = 00000000;
	$startPos2 = Inflatus("foo.z", "foo2",  $startPos1, $defSize);

	print "\n--DONE--\n\n";
}


#############################################################################
#
#############################################################################
sub GatherData {
	my ($Path, $Datf, $Info) = @_;

	my $localStartTime = time();

	if ($Path ne "" && $Datf ne "") {
		print "\n!! Error: Conflicting arguments! Exiting.\n\n"; exit 1;
	}

	%$Info = (
		Path => $Path,
		Datf => $Datf,
		Data => [],
		foundFiles => 0,
		foundDirs  => 0,
		foundBad   => 0,
		foundBytes => 0,
	);

	###########################################################################
	# Gather data
	###########################################################################
	print "-- Delta Mode --\n";

	# Read data
	if    ($Path ne "") {
		my $rc = ReadDataFromFilesystem ($Info);
	}
	elsif ($Datf ne "") {
		my $rc = ReadStdDataFile ($Info);
	}
	print "\n".("=" x $screenWidth)."\n\n";
	print ">> Processed: $Info->{foundFiles} file(s), $Info->{foundDirs} folder(s) ($Info->{foundBad} unreadable) comprising ".(FmtInt($Info->{foundBytes}))." bytes\n\n";
}


#############################################################################
#
#############################################################################
sub RunDiff {
	my ($PathL, $DatfL, $InfoL, $PathR, $DatfR, $InfoR, $opList) = @_;

	my $localStartTime = time();

	###########################################################################
	# Gather data
	###########################################################################
	print "-- Delta Mode --\n";

	print "\n-- Gathering data for left-hand side:\n\n";
	GatherData ($PathL, $DatfL, $InfoL);
	
	print "\n-- Gathering data for right-hand side:\n\n";
	GatherData ($PathR, $DatfR, $InfoR);

	###########################################################################
	# REFERENCE DUMP (for debugging)
	###########################################################################
	if ($DEBUG) {
		print "\n"."-" x $screenWidth."\n";
		print "-- REF DATA DUMP\n\n";

		foreach (@{$InfoL->{Data}}) {
			print "L: $_->{SigStr};$_->{Size};$_->{ElFull}\n";
		}
		print "\n";
		foreach (@{$InfoR->{Data}}) {
			print "R: $_->{SigStr};$_->{Size};$_->{ElFull}\n";
		}
		print "\n";
	}

	###########################################################################
	# Determine delta
	# Note: Move/copy/same may involve tweaks to attribs/timestamps.
	###########################################################################
	print "-" x $screenWidth."\n";
	print "-- Presorting data\n\n";

	my $arefSortedNamesL = $InfoL->{Data};
	my $arefSortedNamesR = $InfoR->{Data};

	my $arefSortedDigSizeL = [];
	for(sort { $a->{SigStr}.$a->{Size} cmp $b->{SigStr}.$b->{Size} } @{$InfoL->{Data}}) { push @$arefSortedDigSizeL, $_; }
	my $arefSortedDigSizeR = [];
	for(sort { $a->{SigStr}.$a->{Size} cmp $b->{SigStr}.$b->{Size} } @{$InfoR->{Data}}) { push @$arefSortedDigSizeR, $_; }
	
	my $arefData = $arefSortedNamesL;
	my @arrL;
	for (my $i = 0; $i < scalar (@$arefData); $i++) {
		push @arrL, "".
			$$arefData[$i]{SigStr}.$colSep.
			($BINARY_PRINT ?
				(
					#$$arefData[$i]{TimeA}.$colSep.
					$$arefData[$i]{TimeM}.$colSep.
					$$arefData[$i]{TimeC}.$colSep.
					$$arefData[$i]{Attr}.$colSep.
					$$arefData[$i]{Size}.$colSep
				):
				(
					#TimeToString(hex($$arefData[$i]{TimeA})).$colSep.
					TimeToString(hex($$arefData[$i]{TimeM})).$colSep.
					TimeToString(hex($$arefData[$i]{TimeC})).$colSep.
					Win32AttribsToString(hex($$arefData[$i]{Attr})).$colSep.
					sprintf ("%015s", IntToHex($$arefData[$i]{Size})).$colSep
				)
			).
			$$arefData[$i]{ElFull};
	}
	
	$arefData = $arefSortedNamesR;
	my @arrR;
	for (my $i = 0; $i < scalar (@$arefData); $i++) {
		push @arrR, "".
			$$arefData[$i]{SigStr}.$colSep.
			($BINARY_PRINT ?
				(
					#$$arefData[$i]{TimeA}.$colSep.
					$$arefData[$i]{TimeM}.$colSep.
					$$arefData[$i]{TimeC}.$colSep.
					$$arefData[$i]{Attr}.$colSep.
					$$arefData[$i]{Size}.$colSep
				):
				(
					#TimeToString(hex($$arefData[$i]{TimeA})).$colSep.
					TimeToString(hex($$arefData[$i]{TimeM})).$colSep.
					TimeToString(hex($$arefData[$i]{TimeC})).$colSep.
					Win32AttribsToString(hex($$arefData[$i]{Attr})).$colSep.
					sprintf ("%015s", IntToHex($$arefData[$i]{Size})).$colSep
				)
			).
			$$arefData[$i]{ElFull};
	}
	
	print "-" x $screenWidth."\n";
	my @diffs     = diff( \@arrL, \@arrR );

	print "-- Finding diffs\n\n";
	if (scalar @diffs == 0) {
		print "-- ** NO DIFFERENCES **\n\n";
	}
	else {
		print "!! ** DIFFERENCES FOUND **\n\n";
		my $cnt = 0;
		foreach my $hunk (@diffs) {
			print "-- Diff hunk $cnt\n";
			foreach my $part (@$hunk) {
				my ($op, $line, $data) = @$part;
				$line++;
				print "$op, $line, $data\n";
			}
			print "\n";
			$cnt++;
		}
	}

}


#############################################################################
#
#############################################################################
sub RunDelta {
	my ($PathL, $DatfL, $InfoL, $PathR, $DatfR, $InfoR, $opList) = @_;

	my $localStartTime = time();

	###########################################################################
	# Gather data
	###########################################################################
	print "-- Delta Mode --\n";

	print "\n-- Gathering data for left-hand side:\n\n";
	GatherData ($PathL, $DatfL, $InfoL);
	
	print "\n-- Gathering data for right-hand side:\n\n";
	GatherData ($PathR, $DatfR, $InfoR);

	###########################################################################
	# REFERENCE DUMP (for debugging)
	###########################################################################
	if ($DEBUG) {
		print "\n"."-" x $screenWidth."\n";
		print "-- REF DATA DUMP\n\n";

		foreach (@{$InfoL->{Data}}) {
			print "L: $_->{SigStr};$_->{Size};$_->{ElFull}\n";
		}
		print "\n";
		foreach (@{$InfoR->{Data}}) {
			print "R: $_->{SigStr};$_->{Size};$_->{ElFull}\n";
		}
		print "\n";
	}

	###########################################################################
	# Determine delta
	# Note: Move/copy/same may involve tweaks to attribs/timestamps.
	###########################################################################
	print "-" x $screenWidth."\n";
	print "-- Presorting data\n\n";

	my $arefSortedNamesL = $InfoL->{Data};
	my $arefSortedNamesR = $InfoR->{Data};

	my $arefSortedDigSizeL = [];
	for(sort { $a->{SigStr}.$a->{Size} cmp $b->{SigStr}.$b->{Size} } @{$InfoL->{Data}}) { push @$arefSortedDigSizeL, $_; }
	my $arefSortedDigSizeR = [];
	for(sort { $a->{SigStr}.$a->{Size} cmp $b->{SigStr}.$b->{Size} } @{$InfoR->{Data}}) { push @$arefSortedDigSizeR, $_; }


	###########################################################################
	#### Gross comparison
	#### Walk the "new" tree (first pass), look for unchanged items versus "old" tree (sort by name):
	###########################################################################
	{
		print "-" x $screenWidth."\n";
		print "-- PROCESS_UNCHANGED\n";
		my $stepCnt = 0;
		my $iLstart = 0;
		for (my $iR = 0; $iR < scalar @{$arefSortedNamesR}; $iR++) {
			my $hrefR = @{$arefSortedNamesR}[$iR];
			for (my $iL = $iLstart; $iL < scalar @{$arefSortedNamesL}; $iL++) {
				my $hrefL = @{$arefSortedNamesL}[$iL];
				my $cmpdiff = ( $hrefR->{ElFull} cmp $hrefL->{ElFull} );
				$stepCnt++;
				if ($cmpdiff > 0) { # thingy R < thingy L (ends loop)
					$iLstart++;
				}
				elsif    ($cmpdiff < 0) { # thingy R < thingy L (try again)
					last; # overshot, don't increment iLstart
				}
				else {  # thingy R == thingy L (ends loop)
					if ($hrefR->{ElType} == T_NONE || $hrefL->{ElType} == T_NONE) {
						$hrefR->{Match} = $hrefL->{Match} = "p";
						$hrefR->{MatchSrc} = $hrefL;
					}
					elsif ($hrefR->{ElType} != $hrefL->{ElType}) {
						#$hrefR->{Match} = $hrefL->{Match} = "d";
					}
					elsif ($hrefR->{SigStr}.$hrefR->{Size} eq $hrefL->{SigStr}.$hrefL->{Size}) {

						$hrefR->{Match} = $hrefL->{Match} = "u";
						$hrefR->{MatchSrc} = $hrefL;

						if ( ($hrefR->{Attr}  ne $hrefL->{Attr} ) ||  # Check attributes
							 #($hrefR->{TimeA} ne $hrefL->{TimeA}) ||  # Check access time
							 #($hrefR->{TimeC} ne $hrefL->{TimeC}) ||  # Check creation time
							 (($hrefR->{ElType} != T_DIR) && ($hrefR->{TimeM} ne $hrefL->{TimeM}))     # Check modify time except for dirs
							) {
							$hrefR->{FixMetadata}  = 1;
						}
						else {
							$hrefR->{FixMetadata}  = 0;
						}
					}
					else {
						$hrefR->{Match} = $hrefL->{Match} = "f";
						$hrefR->{MatchSrc} = $hrefL;
					}
					$iLstart++;
					last; # adds a marginal benefit
				}
			}
		}
		print "\n-- Executed in $stepCnt steps\n\n";
	}

	###########################################################################
	#### Comparison of sigs+sizes
	#### Walk the "new" tree ("" or "f"), look for moved/copied files versus "old" tree (sort by Digest+Size for speed):
	###########################################################################
	{
		print "-" x $screenWidth."\n";
		print "-- PROCESS_MOVE_COPY\n";
		my $stepCnt = 0;
		my $iLstart = 0;
		for (my $iR = 0; $iR < scalar @{$arefSortedDigSizeR}; $iR++) {
			my $hrefR = @{$arefSortedDigSizeR}[$iR];
			if ($hrefR->{ElType} != T_FILE) { next; } # only do the loop for files
			for (my $iL = $iLstart; $iL < scalar @{$arefSortedDigSizeL}; $iL++) {
				my $hrefL = @{$arefSortedDigSizeL}[$iL];

				my $cmpdiff = ( $hrefR->{SigStr}.$hrefR->{Size} cmp $hrefL->{SigStr}.$hrefL->{Size} );
				$stepCnt++;
				if ($cmpdiff > 0) { # thingy R < thingy L (ends loop)
					$iLstart++;
				}
				elsif    ($cmpdiff < 0) { # thingy R < thingy L (try again)
					last; # overshot, don't increment iLstart
				}
				elsif ( ($hrefR->{Match} ne "".M_NONE && $hrefR->{Match} ne "f") ) {
					next; # Ignoring things without issues
				}
				elsif ( ($hrefR->{ElType} != T_FILE || $hrefL->{ElType} != T_FILE) ) {
					next; # Ignoring non-files
				}
				else {  # thingy R == thingy L (ends loop)
					if (($hrefR->{ElType} == $hrefL->{ElType}) &&
						($hrefR->{SigStr}.$hrefR->{Size} eq $hrefL->{SigStr}.$hrefL->{Size}) ) {

						$hrefR->{Match} = "m";
						# $hrefR->{Match} = "m $hrefR->{ElFull}";
						$hrefR->{MatchSrc} = $hrefL;

						if ( ($hrefR->{Attr}  ne $hrefL->{Attr} ) ||  # Check attributes
							 #($hrefR->{TimeA} ne $hrefL->{TimeA}) ||  # Check access time
							 #($hrefR->{TimeC} ne $hrefL->{TimeC}) ||  # Check creation time
							 (($hrefR->{ElType} != T_DIR) && ($hrefR->{TimeM} ne $hrefL->{TimeM}))     # Check modify time except for dirs
							) {
							$hrefR->{FixMetadata}  = 1;
						}
						else {
							$hrefR->{FixMetadata}  = 0;
						}

						if ($hrefL ->{Match} =~ /^m/) {
							$hrefL ->{Match} = "c";
						}
						elsif ($hrefL->{Match} eq "".M_NONE) {
							$hrefL ->{Match} = "m";
						}
						elsif ($hrefL->{Match} eq "f") {
							$hrefL ->{Match} = "m";
						}
						else {
							$hrefR ->{Match} = "c";
						}

						# $iLstart++;
						last; # adds a marginal benefit
					}
				}
			}
		}
		print "\n-- Executed in $stepCnt steps\n\n";
	}

	###########################################################################
	# Display results
	###########################################################################
	if ($DEBUG) {
		print "-" x $screenWidth."\n";

		print "L: PATH = ".($InfoL->{Path})."  ---   ".($InfoL->{Datf})."\n";
		foreach (@{$arefSortedNamesL}) {
			print "".sprintf("L: %-24s:$_->{SigStr};$_->{Size};$_->{ElFull}\n", $_->{Match});
		} print "\n";

		print "R: PATH = ".($InfoR->{Path})."  ---   ".($InfoR->{Datf})."\n";
		foreach (@{$arefSortedNamesR}) {
			my $detail = "";
			if ($_->{Match} eq "m") {
				$detail = $_->{MatchSrc}->{ElFull};
			}
			print "".sprintf("R: %-24s:$_->{SigStr};$_->{Size};$_->{ElFull}\n", $_->{Match}." ".$detail);
		} print "\n";
	}

	###########################################################################
	# Dump execution order
	###########################################################################

	@$opList = ();
	
	my $statErrCnt  = 0;
	my $statSameCnt = 0;
	my $statMoveCnt = 0;
	my $statCopyCnt = 0;
	my $statDelCnt  = 0;
	my $statNewCnt  = 0;
	my $statUpdCnt  = 0;
	my $statMetaCnt = 0;

	######### Unchanged #######################################################
	foreach (@{$arefSortedNamesR}) {
		if ($_->{Match} eq "u" && !$_->{FixMetadata}) {# Just update metadata
			if ($DEBUG) { print "-same-: $_->{SigStr};$_->{Size};$_->{ElFull}\n"; }
			push @$opList, {
				op       => OP_SAME,
				type     => $_->{ElType},
				src      => "",
				tgt      => $_->{ElFull},
				attrVal  => hex($_->{Attr} ),
				timeValA => hex($_->{TimeA}),
				timeValM => hex($_->{TimeM}),
				timeValC => hex($_->{TimeC}),
				sigType  => $_->{SigType},
				sigSize  => $_->{SigSize},
				sigData  => $_->{SigData},
				sizeNorm => HexToInt($_->{Size}),
				sizeComp => HexToInt("0x0"),
				dOffset  => HexToInt("0x0"),
			};
			$statSameCnt++;
		}
	}
	if ($DEBUG) { print "\n"; }

	######### Problems ########################################################
	foreach (@{$arefSortedNamesR}) {
		if ($_->{Match} eq "p") {
			if ($DEBUG) { print "ERROR: $_->{SigStr};$_->{Size};$_->{ElFull}\n"; }
			push @$opList, {
				op       => OP_UNDEF,
				type     => $_->{ElType},
				src      => $_->{MatchSrc}->{ElFull},
				tgt      => $_->{ElFull},
				attrVal  => hex($_->{Attr} ),
				timeValA => hex($_->{TimeA}),
				timeValM => hex($_->{TimeM}),
				timeValC => hex($_->{TimeC}),
				sigType  => $_->{SigType},
				sigSize  => $_->{SigSize},
				sigData  => $_->{SigData},
				sizeNorm => HexToInt($_->{Size}),
				sizeComp => HexToInt("0x0"),
				dOffset  => HexToInt("0x0"),
			};
			$statErrCnt++;
		}
	}
	if ($DEBUG) { print "\n"; }

	######### Move or Copy ####################################################
	foreach (@{$arefSortedNamesR}) { # only files
		if ($_->{Match} eq "m" || $_->{Match} eq "c") {
			if ($_->{MatchSrc}->{Match} eq "m" ) {
			if ($DEBUG) { print "MOVE--: $_->{SigStr};$_->{Size};$_->{MatchSrc}->{ElFull}  -->  $_->{ElFull} \n"; }
				push @$opList, {
					op       => OP_MOVE,
					type     => $_->{ElType},
					src      => $_->{MatchSrc}->{ElFull},
					tgt      => $_->{ElFull},
					attrVal  => hex($_->{Attr} ),
					timeValA => hex($_->{TimeA}),
					timeValM => hex($_->{TimeM}),
					timeValC => hex($_->{TimeC}),
					sigType  => $_->{SigType},
					sigSize  => $_->{SigSize},
					sigData  => $_->{SigData},
					sizeNorm => HexToInt($_->{Size}),
					sizeComp => HexToInt("0x0"),
					dOffset  => HexToInt("0x0"),
				};
				$statMoveCnt++;
			}
			else {
			if ($DEBUG) { print "COPY--: $_->{SigStr};$_->{Size};$_->{MatchSrc}->{ElFull}  -->  $_->{ElFull} \n"; }
				push @$opList, {
					op       => OP_COPY,
					type     => $_->{ElType},
					src      => $_->{MatchSrc}->{ElFull},
					tgt      => $_->{ElFull},
					attrVal  => hex($_->{Attr} ),
					timeValA => hex($_->{TimeA}),
					timeValM => hex($_->{TimeM}),
					timeValC => hex($_->{TimeC}),
					sigType  => $_->{SigType},
					sigSize  => $_->{SigSize},
					sigData  => $_->{SigData},
					sizeNorm => HexToInt($_->{Size}),
					sizeComp => HexToInt("0x0"),
					dOffset  => HexToInt("0x0"),
				};
				$statCopyCnt++;
			}
		}
	}
	if ($DEBUG) { print "\n"; }

	######### Delete ##########################################################
	foreach (@{$arefSortedNamesL}) {  ## Do this after all moves and copies are done ##
		if ($_->{Match} eq "".M_NONE || $_->{Match} eq "c") {
			if ($DEBUG) { print "DELETE: $_->{SigStr};$_->{Size};$_->{ElFull}\n"; }
			push @$opList, {
				op       => OP_REMOVE,
				type     => $_->{ElType},
				src      => "",
				tgt      => $_->{ElFull},
				attrVal  => hex($_->{Attr} ),
				timeValA => hex($_->{TimeA}),
				timeValM => hex($_->{TimeM}),
				timeValC => hex($_->{TimeC}),
				sigType  => $_->{SigType},
				sigSize  => $_->{SigSize},
				sigData  => $_->{SigData},
				sizeNorm => HexToInt($_->{Size}),
				sizeComp => HexToInt("0x0"),
				dOffset  => HexToInt("0x0"),
			};
			$statDelCnt++;
		}
	}
	if ($DEBUG) { print "\n"; }

	######### Create ##########################################################
	foreach (@{$arefSortedNamesR}) {
		if ($_->{Match} eq "".M_NONE) {
			if ($DEBUG) { print "CREATE: $_->{SigStr};$_->{Size};$_->{ElFull}\n"; }
			push @$opList, {
				op       => OP_CREATE,
				type     => $_->{ElType},
				src      => "",
				tgt      => $_->{ElFull},
				attrVal  => hex($_->{Attr} ),
				timeValA => hex($_->{TimeA}),
				timeValM => hex($_->{TimeM}),
				timeValC => hex($_->{TimeC}),
				sigType  => $_->{SigType},
				sigSize  => $_->{SigSize},
				sigData  => $_->{SigData},
				sizeNorm => HexToInt($_->{Size}),
				sizeComp => HexToInt("0x0"),
				dOffset  => HexToInt("0x0"),
			};
			$statNewCnt++;
		}
	}
	if ($DEBUG) { print "\n"; }

	######### Update ##########################################################
	foreach (@{$arefSortedNamesR}) {
		if ($_->{Match} eq "f") {
			if ($DEBUG) { print "UPDATE: $_->{SigStr};$_->{Size};$_->{ElFull}\n"; }
			push @$opList, {
				op       => OP_UPDATE,
				type     => $_->{ElType},
				src      => $_->{MatchSrc}->{ElFull},
				tgt      => $_->{ElFull},
				attrVal  => hex($_->{Attr} ),
				timeValA => hex($_->{TimeA}),
				timeValM => hex($_->{TimeM}),
				timeValC => hex($_->{TimeC}),
				sigType  => $_->{SigType},
				sigSize  => $_->{SigSize},
				sigData  => $_->{SigData},
				sizeNorm => HexToInt($_->{Size}),
				sizeComp => HexToInt("0x0"),
				dOffset  => HexToInt("0x0"),
			};
			$statUpdCnt++;
		}
	}
	if ($DEBUG) { print "\n"; }

	######### Update Metadata ONLY ############################################
	foreach (@{$arefSortedNamesR}) {
		if ($_->{Match} eq "u" && $_->{FixMetadata}) { # Just update metadata
			if ($DEBUG) { print "-meta-: $_->{SigStr};$_->{Size};$_->{ElFull}\n"; }
			push @$opList, {
				op       => OP_FIXMETA,
				type     => $_->{ElType},
				src      => "",
				tgt      => $_->{ElFull},
				attrVal  => hex($_->{Attr} ),
				timeValA => hex($_->{TimeA}),
				timeValM => hex($_->{TimeM}),
				timeValC => hex($_->{TimeC}),
				sigType  => $_->{SigType},
				sigSize  => $_->{SigSize},
				sigData  => $_->{SigData},
				sizeNorm => HexToInt($_->{Size}),
				sizeComp => HexToInt("0x0"),
				dOffset  => HexToInt("0x0"),
			};
			$statMetaCnt++;
		}
	}
	if ($DEBUG) { print "\n"; }

	######### You can push operations onto the end of this list as you go #####

	if ($VERBOSE) {
		DumpOpList($opList);
	}

	print "\n";
	print "-" x $screenWidth."\n";
	print "Results:\n";
	print "    Moved  : ".sprintf("%6d",$statMoveCnt)."\n";
	print "    Copied : ".sprintf("%6d",$statCopyCnt)."\n";
	print "    Deleted: ".sprintf("%6d",$statDelCnt )."\n";
	print "    Created: ".sprintf("%6d",$statNewCnt )."\n";
	print "    Updated: ".sprintf("%6d",$statUpdCnt )."\n";
	print "    FixMeta: ".sprintf("%6d",$statMetaCnt)."\n";
	print "    -Same- : ".sprintf("%6d",$statSameCnt)."\n";
	print "    Errors : ".sprintf("%6d",$statErrCnt )."\n";
	print "\n";
	

	#########################################################################
	# Report and exit
	#########################################################################

	my $elapsedTime = time()-$localStartTime+0.000001; # Strange output without slight twiddle factor here
	my $hours = int($elapsedTime/(60*60));
	my $mins  = int((($elapsedTime)/(60*60)-$hours)*60);
	my $secs  = int(((($elapsedTime)/(60*60)-$hours)*60-$mins)*60);
	my $elapsedTimeFmt = sprintf("%d:%02d:%02d", $hours, $mins, $secs);

	print "=" x $screenWidth."\n";
	print ">>>\n";
	print ">>> Elapsed time: $elapsedTimeFmt\n";
	print ">>>\n";
	print "=" x $screenWidth."\n";
	print "\n";
}


#############################################################################
# Dump the operations list
#############################################################################
sub DumpOpList {
	my ($aref) = @_;
	print "-" x $screenWidth."\n";
	foreach my $href (@$aref) {
		if ($href->{op} != OP_SAME) {
			my $opText   = Printable_const_OP ($href->{op});
			my $typeText = Printable_const_T ($href->{type});

			print ">> ".sprintf("%-10s", $opText)." ".sprintf("%2d, %2d", $href->{sigType}, $href->{sigSize}).
				"  (".($href->{sigSize} > 0? unpack("H*", $href->{sigData}):"+" x 32).") ".
				sprintf("%-7s", $typeText)."  \"$href->{src}\"  \"$href->{tgt}\"\n";
		}
	}
	print "-" x $screenWidth."\n";
}


#############################################################################
# Create a backup set
#############################################################################
sub CreateBackup {
	my ($backupFile, $infoText, $InfoLref, $InfoRref, $opListRef) = @_;

	if ($backupFile eq "") { return 1; }

	my $localStartTime = time();

	#######################################################################
	# Header structure (start of backup file):
	#   magic    (4 bytes)  = "MFTH"
	#   version  (4 bytes)  = major.minor (2 bytes each)
	#   iSize    (4 bytes)  = Size of index
	#   iOffset  (4 bytes)  = Abs offset to index start
	#   infotext (strz)
	#
	# Index structure (per element in this data store):
	#	op       (1 byte)   = encoded op type (OP_MOVE, OP_COPY, etc.)
	#	type     (1 bytes)  = encoded data type (T_FILE, T_DIR, etc.)
	#	src      (strz)     
	#	tgt      (strz)     
	#	attrVal  (2 bytes)
	#	timeValA (4 bytes)
	#	timeValM (4 bytes)
	#	timeValC (4 bytes)
	#	sigType  (1 byte)   # T_FILE ONLY # [0] = no sig, [1] = MD5, [2-...] = undefined
	#	sigSize  (2 bytes)  # T_FILE ONLY # Size of sig storage in bytes (up to 65535 bytes). 0 = no sig (128 bits for MD5 = 16 bytes of binary data)
	#	sigData  (n bytes)  # T_FILE ONLY # Sig of Norm data, in whole bytes.
	#	sizeNorm (8 bytes)  # T_FILE ONLY # if zero, offset is unused
	#	sizeComp (8 bytes)  # T_FILE ONLY # if zero, offset is unused
	#	dOffset  (8 bytes)  # T_FILE ONLY # Abs offset of start of compressed data
	#
	#######################################################################

	my $curPos = 0; # will use as we write compressed data as well

	print "\nBACKING UP to $backupFile\n\n";
	print "Backup file comment: \"$infoText\"\n";

	open FOUT, ">$backupFile" or die "!! Error: Cannot open $backupFile\n";
	close FOUT; # Effectively a file-clearing/file-creating touch

	open FOUT, "+<$backupFile" or die "!! Error: Cannot open $backupFile\n";
	binmode FOUT;
	
	my $headerSize = 0;
	my $indexSize  = 0;
	my $indexStart = 0;
	
	if ($DEBUG) { print "Writing empty header starting at: ".tell(FOUT)."\n"; }
	my $headerBuffer = CreatePackedHeaderBlock ($MAGIC, $VERSION, $indexSize, $indexStart, $infoText);
	$headerSize = length ($headerBuffer);
	$curPos += $headerSize;
	print FOUT chr(0xF0) x ($headerSize); # empty, for now

	$indexStart = $curPos;
	if ($DEBUG) { print "Writing empty index starting at: ".tell(FOUT)."\n"; }
	foreach my $href ( @$opListRef ) {
		my $tBuf = CreatePackedIndexBlock($href);
		$curPos += length ($tBuf);
	}
	$indexSize = $curPos - $indexStart;
	print FOUT chr(0x5A) x ($indexSize); # empty, for now
	
	if ($DEBUG) { print "Writing data starting at: ".tell(FOUT)."\n"; }

	foreach my $href ( @$opListRef ) {
		if (($href->{op} == OP_UPDATE || $href->{op} == OP_CREATE) && ($href->{type} == T_FILE)) { # A file that needs backing up
			############################################################################
			# Valid values for deflation levels are -1 through 9, with certain defines:
			# -1 = Z_DEFAULT_COMPRESSION
			#  0 = Z_NO_COMPRESSION
			#  1 = Z_BEST_SPEED
			#  ......
			#  9 = Z_BEST_COMPRESSION
			############################################################################
			my $infile = "$InfoRref->{Path}/$href->{tgt}";
			my $deflationlevel = Z_DEFAULT_COMPRESSION;
			open FIN, "$infile" or die "!! Error: Cannot open $infile\n";
			binmode FIN;
			my $x = deflateInit(-Level => $deflationlevel) or die "!! Error: Cannot create a deflation stream\n";
			my $inputBytes = 0;
			my $outputBytes = 0;
			my $input = '';
			my ($output, $status);
			while (read(FIN, $input, DEFAULT_FILEIO_CHUNK_SIZE)) {
				$inputBytes += length($input);
				($output, $status) = $x->deflate(\$input);
				$outputBytes += length($output);
				$status == Z_OK or die "deflation failed\n";
				print FOUT $output;
			}
			($output, $status) = $x->flush();
			$outputBytes += length($output);
			$status == Z_OK	or die "deflation failed\n";
			print FOUT $output;
			close FIN;
			$href->{sizeComp} = $outputBytes;
			$href->{dOffset} = $curPos;
			$curPos += $outputBytes; # Always update this *after* setting dOffset
		}
	}
	if ($DEBUG) { print "Done Writing data at: ".tell(FOUT)."\n"; }

	if (!seek(FOUT, 0, 0)) { print "seek failed\n"; }
	if ($DEBUG) { print "Writing final header: ".tell(FOUT)."\n"; }
	print FOUT CreatePackedHeaderBlock ($MAGIC, $VERSION, $indexSize, $indexStart, $infoText);
	
	if (!seek(FOUT, $indexStart, 0)) { print "seek failed\n"; }
	if ($DEBUG) { print "Writing final index starting at: ".tell(FOUT)."\n"; }
	foreach my $href ( @$opListRef ) {
		print FOUT CreatePackedIndexBlock($href); # This works as long as the only changes are of the same length
	}

	close FOUT;

	#########################################################################
	# Report and exit
	#########################################################################

	my $elapsedTime = time()-$localStartTime+0.000001; # Strange output without slight twiddle factor here
	my $hours = int($elapsedTime/(60*60));
	my $mins  = int((($elapsedTime)/(60*60)-$hours)*60);
	my $secs  = int(((($elapsedTime)/(60*60)-$hours)*60-$mins)*60);
	my $elapsedTimeFmt = sprintf("%d:%02d:%02d", $hours, $mins, $secs);

	print "=" x $screenWidth."\n";
	print ">>>\n";
	print ">>> Elapsed time: $elapsedTimeFmt\n";
	print ">>>\n";
	print "=" x $screenWidth."\n";
	print "\n";

	return 0;
}


#############################################################################
# 
#############################################################################
sub CreatePackedHeaderBlock {
	my ($magic, $ver, $idxSize, $idxOffset, $info) = @_;

	my $verMajor = int($ver);
	my $verMinor = ($ver - $verMajor)*1000;
	$verMinor = int($verMinor + .5 * ($verMinor <=> 0)); # Rounding, from PerlFAQ

	my $buf = "";
	$buf .= $magic;
	$buf .= pack ("SS", $verMajor, $verMinor);
	$buf .= pack ("L",  $idxSize);
	$buf .= pack ("L",  $idxOffset);
	$buf .= pack ("Z*", $info);
	
	return $buf;
}


#############################################################################
# 
#############################################################################
sub CreatePackedIndexBlock {
	my ($href) = @_;
	my $buf = "";
	$buf .= pack ("C",  $href->{op});
	$buf .= pack ("C",  $href->{type});
	$buf .= pack ("Z*", $href->{src});
	$buf .= pack ("Z*", $href->{tgt});
	$buf .= pack ("S",  $href->{attrVal });
	$buf .= pack ("L",  $href->{timeValA});
	$buf .= pack ("L",  $href->{timeValM});
	$buf .= pack ("L",  $href->{timeValC});
	$buf .= pack ("c",  $href->{sigType });
	$buf .= pack ("S",  $href->{sigSize });
	$buf .= $href->{sigData};
	$buf .= pack ("LL", BigIntToIntLoHi($href->{sizeNorm}));
	$buf .= pack ("LL", BigIntToIntLoHi($href->{sizeComp}));
	$buf .= pack ("LL", BigIntToIntLoHi($href->{dOffset}));
	
	$href->{entrySize} = length ($buf) + 2;
	$buf = pack ("S",  $href->{entrySize}).$buf; # prepend entry size
	
	return $buf;
}


#############################################################################
# 
#############################################################################
sub UnpackIndexBlock {
	my ($href, $buf) = @_;
	my $idx = 0;
	$href->{op}       = unpack "C",  substr ($buf, $idx, 1); $idx += 1;
	$href->{type}     = unpack "C",  substr ($buf, $idx, 1); $idx += 1;
	$href->{src}      = unpack "Z*", substr ($buf, $idx);    $idx += length($href->{src})+1;
	$href->{tgt}      = unpack "Z*", substr ($buf, $idx);    $idx += length($href->{tgt})+1;
	$href->{attrVal } = unpack "S",  substr ($buf, $idx, 2); $idx += 2;
	$href->{timeValA} = unpack "L",  substr ($buf, $idx, 4); $idx += 4;
	$href->{timeValM} = unpack "L",  substr ($buf, $idx, 4); $idx += 4;
	$href->{timeValC} = unpack "L",  substr ($buf, $idx, 4); $idx += 4;
	$href->{sigType } = unpack "c",  substr ($buf, $idx, 1); $idx += 1;
	$href->{sigSize } = unpack "S",  substr ($buf, $idx, 2); $idx += 2;
	$href->{sigData}  = substr ($buf, $idx, $href->{sigSize}); $idx += $href->{sigSize};
	$href->{sizeNorm} = IntLoHiToBigInt(unpack "LL", substr ($buf, $idx, 8)); $idx += 8;
	$href->{sizeComp} = IntLoHiToBigInt(unpack "LL", substr ($buf, $idx, 8)); $idx += 8;
	$href->{dOffset } = IntLoHiToBigInt(unpack "LL", substr ($buf, $idx, 8)); $idx += 8;
	
	return $idx;
}


#############################################################################
# Restore from a backup set and a basis fileystem tree
#############################################################################
sub RestoreBackup {
	my ($restorePath, $backupFile) = @_;

	if ($restorePath eq "") { return 1; }

	my $localStartTime = time();
	
	print "\nRESTORING from $backupFile to $restorePath\n\n";

	my $input = '';

	open FIN, "$backupFile" or die "!! Error: Cannot open $backupFile\n";
	binmode FIN;
	
	read FIN, $input, length($MAGIC);
	if ($DEBUG) { print "Magic         = $input (versus '$MAGIC')\n"; }
	$input eq $MAGIC or die "The magic is gone, baby!\n";
	read FIN, $input, 2+2+4+4;
	my ($verMajor, $verMinor, $indexSize, $indexStart) = unpack "SSLL", $input;
	if ($DEBUG) { print "Version       = ".sprintf("%d.%02d", $verMajor, $verMinor)."\n"; }
	if ($DEBUG) { print "Index start   = $indexStart\n"; }
	if ($DEBUG) { print "Index size    = $indexSize\n"; }
	if ($DEBUG) { print "Data Start    = ".($indexStart + $indexSize)."\n"; }
	if ($DEBUG) { print "InfoText Size = ".($indexStart - tell(FIN))."\n"; }
	read FIN, $input, $indexStart - tell(FIN);
	my ($infoText) = unpack "Z*", $input;
	if ($DEBUG) { print "InfoText Data = $infoText\n"; }
	if ($DEBUG) { print "End of header at ".tell(FIN)."\n"; }

	print "Backup file comment: \"$infoText\"\n";
	print "\n";
	
	my @newOpList = ();

	my $idx = 0;	
	my $curPos = tell(FIN);
	while (tell(FIN) < $indexStart + $indexSize) {
		if (!seek(FIN, $curPos, 0)) { print "seek failed\n"; }
		read FIN, $input, 2;
		my $indexBlockSize = unpack "S", $input;
		read FIN, $input, $indexBlockSize - 2;
		$curPos = tell(FIN); # this is where we will be next
		my %newhash;
		UnpackIndexBlock (\%newhash, $input);
		push @newOpList, \%newhash;
	}
	if ($DEBUG) { print "End of index at ".tell(FIN)."\n"; }

	###########################################################################
	######### SPECIAL: don't remove folders that should remain! ###############
	#### Works around Windows issue: if folder name $a is moved to name $b, 
	#### folder $b is created, contents of $a are moved there and $a is removed.
	#### If however $a == $b except for case, you end up removing $b after!
	#### This code prevents that Windows-only case.
	###########################################################################
	foreach my $op (@newOpList) {
		if ($op->{op} == OP_REMOVE && $op->{type} == T_DIR) {
			foreach my $ck (@newOpList) {
				if ($ck->{op} == OP_CREATE && $ck->{type} == T_DIR) {
					if (lc($op->{tgt}) eq lc($ck->{tgt})) {
						$op->{op}=OP_SAME;
						$ck->{op}=OP_MOVE;
						$ck->{src}=$op->{tgt};
						print "!! UPDATED OP: RENAME $op->{tgt} to $ck->{tgt}\n";
					}
				}
			}
		}
	}
	
	if ($VERBOSE) {
		DumpOpList(\@newOpList);
	}

	if ($restorePath =~ /^([a-z]:)[\\\/]$/i) { $restorePath = $1 };
	
	foreach my $href (@newOpList) {
		if    ($href->{op} == OP_MOVE) {
			my $restorePathPart = "$restorePath/$href->{tgt}";
			$restorePathPart =~ s/[\/\\][^\/\\]*$//;
			if (!-e $restorePathPart) {
				#print "!! Warning: Creating partial restore path: $restorePathPart\n";
				mkpath($restorePathPart);
			}
			if (-e "$restorePath/$href->{tgt}" && lc "$restorePath/$href->{tgt}" ne lc "$restorePath/$href->{src}") {
				do { $href->{intermediate} = "$restorePathPart/".sprintf("TEMP_%04x%04x", rand(0x10000), rand(0x10000));}
				while (-e $href->{intermediate});
				print "-- Note: MOVE would overwrite $restorePath/$href->{tgt} (using $href->{intermediate})\n";
				SetAttributes("$href->{intermediate}", FILEATTRIB_NORMAL);
				move ("$restorePath/$href->{src}", "$href->{intermediate}");
			}
			else {
				SetAttributes("$restorePath/$href->{tgt}", FILEATTRIB_NORMAL);
				move ("$restorePath/$href->{src}", "$restorePath/$href->{tgt}");
				SetAttributes("$restorePath/$href->{tgt}", $href->{attrVal});
				SetFileTime("$restorePath/$href->{tgt}", $href->{timeValA}, $href->{timeValM}, $href->{timeValC});
			}
		}
		elsif ($href->{op} == OP_COPY) {
			my $restorePathPart = "$restorePath/$href->{tgt}";
			$restorePathPart =~ s/[\/\\][^\/\\]*$//;
			if (!-e $restorePathPart) {
				#print "!! Warning: Creating partial restore path: $restorePathPart\n";
				mkpath($restorePathPart);
			}
			if (-e "$restorePath/$href->{tgt}" && lc "$restorePath/$href->{tgt}" ne lc "$restorePath/$href->{src}") {
				do { $href->{intermediate} = "$restorePathPart/".sprintf("TEMP_%04x%04x", rand(0x10000), rand(0x10000));}
				while (-e $href->{intermediate});
				print "-- Note: COPY would overwrite $restorePath/$href->{tgt} (using $href->{intermediate})\n";
				SetAttributes("$href->{intermediate}", FILEATTRIB_NORMAL);
				copy ("$restorePath/$href->{src}", "$href->{intermediate}");
			}
			else {
				SetAttributes("$restorePath/$href->{tgt}", FILEATTRIB_NORMAL);
				copy ("$restorePath/$href->{src}", "$restorePath/$href->{tgt}");
				SetAttributes("$restorePath/$href->{tgt}", $href->{attrVal});
				SetFileTime("$restorePath/$href->{tgt}", $href->{timeValA}, $href->{timeValM}, $href->{timeValC});
			}
		}
		elsif (($href->{op} == OP_UPDATE || $href->{op} == OP_CREATE) && ($href->{type} == T_FILE)){
			my $restorePathPart = "$restorePath/$href->{tgt}";
			$restorePathPart =~ s/[\/\\][^\/\\]*$//;
			if (!-e $restorePathPart) {
				print "!! Warning: Creating partial restore path: $restorePathPart\n";
				mkpath($restorePathPart);
			}
			
			SetAttributes("$restorePath/$href->{tgt}", FILEATTRIB_NORMAL);

			# Decompress data stream to original name
			open FOUT, ">$restorePath/$href->{tgt}" or die "!! Error: Cannot open $restorePath/$href->{tgt}\n";
			binmode FOUT;
			if (!seek(FIN, $href->{dOffset}, 0)) { print "seek failed\n"; }
			my $x = inflateInit() or die "Cannot create a inflation stream\n";
			my $inputBytes = 0;
			my $outputBytes = 0;
			my $input = '';
			my ($output, $status);
			my $readSize = DEFAULT_FILEIO_CHUNK_SIZE;
			if ($readSize > $href->{sizeComp}) { $readSize = $href->{sizeComp}; }
			my $FINALPASS = 0;
			while (read(FIN, $input, $readSize)) {
				$inputBytes += length($input);
				if ($inputBytes + $readSize > $href->{sizeComp}) { $readSize = $href->{sizeComp} - $inputBytes; }
				if ($inputBytes == $href->{sizeComp}) { $FINALPASS = 1; }
				($output, $status) = $x->inflate(\$input);
				$outputBytes += length($output);
				print FOUT $output if $status == Z_OK or $status == Z_STREAM_END;
				last if $status != Z_OK;
				last if $FINALPASS;
			}
			$status == Z_STREAM_END or die "inflation failed\n";
			close FOUT;
			
			SetAttributes("$restorePath/$href->{tgt}", $href->{attrVal});
			SetFileTime("$restorePath/$href->{tgt}", $href->{timeValA}, $href->{timeValM}, $href->{timeValC});
		}
		elsif (($href->{op} == OP_CREATE) && ($href->{type} == T_DIR)) {
			my $restorePathPart = "$restorePath/$href->{tgt}";
			$restorePathPart =~ s/[\/\\][^\/\\]*$//;
			if (!-e $restorePathPart) {
				#print "!! Warning: Creating partial restore path: $restorePathPart\n";
				mkpath($restorePathPart);
			}
			SetAttributes("$restorePath/$href->{tgt}", FILEATTRIB_DIRECTORY);
			mkdir ("$restorePath/$href->{tgt}");
			SetAttributes("$restorePath/$href->{tgt}", $href->{attrVal});
			SetFileTime("$restorePath/$href->{tgt}", $href->{timeValA}, $href->{timeValM}, $href->{timeValC});
		}
		elsif ($href->{op} == OP_FIXMETA) { # Just fix the metadata
			SetAttributes("$restorePath/$href->{tgt}", $href->{attrVal});
			SetFileTime("$restorePath/$href->{tgt}", $href->{timeValA}, $href->{timeValM}, $href->{timeValC});
		}
		elsif ($href->{op} == OP_REMOVE) { # have to make sure this is in reverse order eventually
			system ("rm -rf \"$restorePath/$href->{tgt}\"");
		}
	}

	# Final moves of files
	print "-- Fixing move/copy special cases\n";
	foreach my $href (@newOpList) {
	if    (defined $href->{intermediate}) {
			my $restorePathPart = "$href->{intermediate}";
			$restorePathPart =~ s/[\/\\][^\/\\]*$//;
			if (!-e $restorePathPart) {
				print "!! Warning: Creating partial restore path: $restorePathPart\n";
				mkpath($restorePathPart);
			}
			SetAttributes("$href->{intermediate}", FILEATTRIB_NORMAL);
			move ("$href->{intermediate}", "$restorePath/$href->{tgt}");
			SetAttributes("$restorePath/$href->{tgt}", $href->{attrVal});
			SetFileTime("$restorePath/$href->{tgt}", $href->{timeValA}, $href->{timeValM}, $href->{timeValC});
		}
	}

	# Final pass to correct directory settings
	print "-- Fixing directory metadata\n";
	foreach my $href (@newOpList) {
	if    ($href->{type} == T_DIR && ($href->{op} == OP_SAME || $href->{op} == OP_CREATE || $href->{op} == OP_FIXMETA)) {
			SetAttributes("$restorePath/$href->{tgt}", $href->{attrVal});
			SetFileTime("$restorePath/$href->{tgt}", $href->{timeValA}, $href->{timeValM}, $href->{timeValC});
		}
	}


	close FIN;
	
	#########################################################################
	# Report and exit
	#########################################################################

	my $elapsedTime = time()-$localStartTime+0.000001; # Strange output without slight twiddle factor here
	my $hours = int($elapsedTime/(60*60));
	my $mins  = int((($elapsedTime)/(60*60)-$hours)*60);
	my $secs  = int(((($elapsedTime)/(60*60)-$hours)*60-$mins)*60);
	my $elapsedTimeFmt = sprintf("%d:%02d:%02d", $hours, $mins, $secs);

	print "=" x $screenWidth."\n";
	print ">>>\n";
	print ">>> Elapsed time: $elapsedTimeFmt\n";
	print ">>>\n";
	print "=" x $screenWidth."\n";
	print "\n";

	return 0;
}


#############################################################################
#
#############################################################################
sub GenerateDataFiles {
	my ($filePrefix, $argvRef) = @_;

	my $localStartTime = time();

	print "-" x $screenWidth."\n";
	print "-- Generating data file(s) --\n\n";

	foreach my $path (@{$argvRef}) {
		if ($filePrefix eq "") {
			my $specialPath = $path;
			$specialPath =~ s/\\/\//g;
			$filePrefix = "treehash-".ManglePath($specialPath);
		}

		my %InfoT = (
			Path       => $path,
			Prefix     => $filePrefix,
			Datf       => "",
			Data       => [],
			foundFiles => 0,
			foundDirs  => 0,
			foundBad   => 0,
			foundBytes => 0,
		);

		print "+" x $screenWidth."\n";
		my $rc = ReadDataFromFilesystem (\%InfoT);
		my $foundFiles = $InfoT{foundFiles};
		my $foundDirs  = $InfoT{foundDirs};
		my $foundBad   = $InfoT{foundBad};
		my $foundBytes = $InfoT{foundBytes};

		#####################################################################
		# Gather statistics
		#####################################################################

		$BytesTotal += $foundBytes;


		#####################################################################
		# Dump output to a file
		#####################################################################

		CreateStdDatFile (\%InfoT);
		if    (defined($opt_alt)) {
			CreateAltDatFile (\%InfoT);
		}

		#####################################################################
		# Write summary of dump
		#####################################################################

		print "\n".("=" x $screenWidth)."\n\n";
		print ">> Processed: $foundFiles file(s), $foundDirs folder(s) ($foundBad unreadable) comprising ".(FmtInt($foundBytes))." bytes\n\n";
	}

	#########################################################################
	# Report and exit
	#########################################################################

	my $elapsedTime = time()-$localStartTime;
	if ($elapsedTime < 1) { $elapsedTime = 0.5; }  # Strange output without slight twiddle factor here
	my $hours = int($elapsedTime/(60*60));
	my $mins  = int((($elapsedTime)/(60*60)-$hours)*60);
	my $secs  = int(((($elapsedTime)/(60*60)-$hours)*60-$mins)*60);
	my $elapsedTimeFmt = sprintf("%d:%02d:%02d", $hours, $mins, $secs);

	my $rate = int(100*$BytesTotal/(1024*1024)/$elapsedTime)/100;

	print "=" x $screenWidth."\n";
	print ">>>\n";
	print ">>> Elapsed time: $elapsedTimeFmt\n";
	print ">>> Processed ".(FmtInt($BytesTotal))." bytes\n";
	print ">>> Average data rate = $rate MB/sec\n";
	print ">>>\n";
	print "=" x $screenWidth."\n";
	print "\n";

	return 0;
}


##############################################################################
#
##############################################################################
sub ReadStdDataFile {
	my ($arefHash) = @_;

	my $dataFile = $arefHash->{Datf};
	my $arefData = $arefHash->{Data};

	my $foundBytes  = 0;
	my $foundDirs   = 0;
	my $foundFiles  = 0;
	my $foundBad    = 0;

	if (! -f $dataFile) {
		print "\n!! Error: $dataFile is not a file, exiting\n\n";
		exit(255);
	}

	print ">> Reading standard data file: $dataFile\n";

	if (! open (FIN, "$dataFile")) {
		print "\nCannot open $dataFile, exiting\n";
		exit(255);
	}
	binmode FIN;

	my $BasePath = "UNDEFINED";

	foreach (<FIN>) {
		chomp;
		if (/^\s*\#\s*BASE PATH: (.*)$/i) {
			$BasePath = $1;
			$BasePath =~ s/\\/\//g;
			$BasePath =~ s/\/$//g;
			next;
		}
		elsif (/^\s*\#/ || /^\s*$/) {
			next;
		}

		my $curLine = $_;
		my @fields = split /;/, $curLine, 7;
		my $elPath = "";
		my $elName = $fields[6];
		my $elementShort = $elName;

		# Used to perform an IsIgnoredElement() check here (deprecated)

		if ($elName =~ /\/ /) {
			print "WEIRD!  $elName\n";
			$elName =~ s/\/ /\//g;
		}

		if ($elName =~ /^(.*)\/([^\/]*)$/) {
			$elPath = $1;
			$elName = $2;
		}

		my $fileSize = HexToInt($fields[5]);
		$foundBytes += $fileSize;

		my $elType = T_NONE;
		if    ($fields[0] !~ /^[0-9A-F\-]+/i) { $foundBad++; }
		elsif ($fields[0] =~ /^[0-9A-F]+/i)   { $foundFiles++; $elType = T_FILE; }
		elsif ($fields[0] =~ /^[\-]+/i)       { $foundDirs++;  $elType = T_DIR; }

		my %data = (  # For a given element
			SigType  => (($fields[0] =~ /^[a-f\d]+$/i)?1:0),
			SigSize  => (($fields[0] =~ /^[a-f\d]+$/i)?(length($fields[0])/2):0),
			SigData  => (($fields[0] =~ /^[a-f\d]+$/i)?(pack "H*", $fields[0]):""),
			SigStr   => $fields[0],  # Will use this as a string in comparisons
			TimeA    => $fields[1],  # Will use this as a string in comparisons
			TimeM    => $fields[2],  # Will use this as a string in comparisons
			TimeC    => $fields[3],  # Will use this as a string in comparisons
			Attr     => $fields[4],  # Will use this as a string in comparisons
			Size     => $fields[5],  # Will use this as a string in comparisons
			ElPath   => $elPath,
			ElName   => $elName,
			ElFull   => $elementShort,
			ElType   => $elType,
			Match    => M_NONE, # No matches to start off with
			MatchLoc => "", # If I have a match, where is it? (opposites should have precedence)
			MatchRef => [], # If I have a match, what is it?
			MyLoc    => "", # To which side do *I* belong?
		);

		push @$arefData, \%data;

	}

	close FIN;

	$arefHash->{Path} = $BasePath;

	$arefHash->{foundFiles} = $foundFiles;
	$arefHash->{foundDirs}  = $foundDirs;
	$arefHash->{foundBad}   = $foundBad;
	$arefHash->{foundBytes} = $foundBytes;

	# Sort the results
	@$arefData = sort {$a->{ElFull} cmp $b->{ElFull}} @$arefData;

	return 0;
}


#############################################################################
#
#############################################################################
sub IsIgnoredElement {
	my ($relName, $arefIgnoredElements) = @_;
	# Inputs must have been stripped of any leading/trailing "/"es
	my $SKIPTHIS = 0;
	foreach (@{$arefIgnoredElements}) {
		my $matchPat = $_;
		if ($relName =~ /$matchPat/i) {
			#print "-- Matched $relName =~ /$matchPat/i\n";
			$SKIPTHIS = 1;
			last;
		}
	}
	return $SKIPTHIS;
}


#############################################################################
#
#############################################################################
sub ReadDataFromFilesystem {
	my ($arefHash) = @_;

	my $path     = $arefHash->{Path};
	my $arefData = $arefHash->{Data};

	my $dataFile = ManglePath($path);
	$arefHash->{DatF} = $dataFile;

	my $origCwd = cwd();

	my @ElementList = ();

    my $foundBytes = 0;

	if (-d $path)  {
		print ">> Reading filesystem - folder: $path\n";
	}
	elsif (-f $path)   {
		print ">> Reading filesystem - file: $path\n";
	}
	else {
		print "!! Error: Invalid argument : $path\n\n";
		return;
	}

	if (-d $path && $path !~ /[\/\\]$/) {
		$path .= "/";
	}
	my $matchPath = quotemeta($path);

	if ($path eq "") {
		print "\n!! Error: No path specified!\n\n";
		exit 1;
	}

	if ($path =~ /^([a-z]\:)/i) {
		chdir("$1/");
	}

	my ($foundFiles, $foundDirs, $foundBad) = findElements ($path, \@ElementList);

	chdir $origCwd;

	#####################################################################
	# Prune out unwanted bits
	#   - and -
	# Parse each file in the found list into an array
	#####################################################################

	foreach my $element (@ElementList) {
		if ($element eq "") { next; }

		my $DataMode = "";
		if ($MP3_DATA_ONLY && $element =~ /\.mp3$/i) {
			$DataMode = "mp3";
		}

		my ($fileSize, $atimeStat, $mtimeStat, $ctimeStat, $w32Attr) = GetFileAttributes($element);
		$foundBytes += $fileSize;

		my $fileSizeHex = sprintf("%010s", IntToHex($fileSize)); # 10 hex digits = sufficient for Windows (1 Tb)

		print "\b" x $screenWidth;
		print ">> Processing $fileSizeHex bytes ";

		my $elementShort = $element;
		$elementShort =~ s/^($matchPath)//;
		$elementShort =~ s/^\///g;
		my $elName = $elementShort;
		my $elPath = "";
		if ($elName =~ /^(.*)\/([^\/]*)$/) {
			$elPath .= "/$1";
			$elName = $2;
		}

		my $sigStr = ();
		my $readBytes = 0;
		($sigStr, $readBytes) = GetMD5Sig($element, $DataMode);
		if ($DataMode eq "mp3") {
			$fileSize = $readBytes; # Since actual hashed size may be smaller
			$fileSizeHex = sprintf("%010s", IntToHex($fileSize)); # 10 hex digits = sufficient for Windows (1 Tb)
		}
		else {
			if ($fileSize != $readBytes) {
				print "\n!! Warning: Normal file has bytes-read mismatch ($fileSize vs $readBytes): $elName\n\n";
			}
			elsif ((-s $element) != $fileSize) {
				print "\n!! Warning: Size mismatch: ".(-s $element)." vs $fileSize\n\n"
			}
		}

		print " [$sigStr] ";

		my $elType = T_NONE;
		if    ($sigStr !~ /^[0-9A-F\-]+/i) { $foundBad++; $foundFiles--; }
		elsif ($sigStr =~ /^[0-9A-F]+/i)   { $elType = T_FILE; }
		elsif ($sigStr =~ /^[\-]+/i)       { $elType = T_DIR; }

		my %data = (  # For a given element
			SigType  => (($sigStr =~ /^[a-f\d]+$/i)?1:0),
			SigSize  => (($sigStr =~ /^[a-f\d]+$/i)?(length($sigStr)/2):0),
			SigData  => (($sigStr =~ /^[a-f\d]+$/i)?(pack "H*", $sigStr):""),
			SigStr   => $sigStr,
			TimeA    => sprintf("%08x",  $atimeStat),
			TimeM    => sprintf("%08x",  $mtimeStat),
			TimeC    => sprintf("%08x",  $ctimeStat),
			Attr     => sprintf("%04x",  $w32Attr),
			Size     => $fileSizeHex,
			ElPath   => $elPath,
			ElName   => $elName,
			ElFull   => $elementShort,
			ElType   => $elType,
			Match    => M_NONE, # No matches to start off with
			MatchLoc => "", # If I have a match, where is it? (opposites should have precedence)
			MatchRef => [], # If I have a match, what is it?
			MyLoc    => "", # To which side do *I* belong?
		);

		push @$arefData, \%data;

	}

	print "\b" x $screenWidth;
	print " "  x $screenWidth;
	print "\b" x $screenWidth;

	$arefHash->{foundFiles} = $foundFiles;
	$arefHash->{foundDirs}  = $foundDirs;
	$arefHash->{foundBad}   = $foundBad;
	$arefHash->{foundBytes} = $foundBytes;

	# Sort the results
	@$arefData = sort {$a->{ElFull} cmp $b->{ElFull}} @$arefData;

	return 0;
}


#############################################################################
#
#############################################################################
sub CreateStdDatFile {
	my ($arefHash) = @_;

	my $path       = $arefHash->{Path};
	my $filePrefix = $arefHash->{Prefix};
	my $arefData   = $arefHash->{Data};
	my $foundFiles = $arefHash->{foundFiles};
	my $foundDirs  = $arefHash->{foundDirs};
	my $foundBad   = $arefHash->{foundBad};
	my $foundBytes = $arefHash->{foundBytes};

	$path =~ s/\\/\//g;

	my $dataFileOUT = "$filePrefix.thd";

	if (! open (FOUT, ">".$dataFileOUT)) {
		print "\nCannot open $dataFileOUT, exiting\n";
		exit(255);
	}
	binmode FOUT;

	print FOUT "#"."-" x $screenWidth."\n";
	print FOUT "#"."\n";
	print FOUT "#"."  Base path: $path\n";
	print FOUT "#"."\n";
	print FOUT "#"."  Processed: $foundFiles file(s), $foundDirs folder(s) ($foundBad unreadable) comprising ".(FmtInt($foundBytes))." bytes\n";
	print FOUT "#"."\n";
	print FOUT "#"."-" x $screenWidth."\n";
	print FOUT "#"."        MD5 signature          |accessT |modifyT |createT |attr|   size   |relative name  \n";
	print FOUT "#"."-" x $screenWidth."\n";
	print FOUT "\n";

	for (my $i = 0; $i < scalar (@$arefData); $i++) {
		print FOUT "".
			$$arefData[$i]{SigStr}.$colSep.
			($BINARY_PRINT ?
				(
					$$arefData[$i]{TimeA}.$colSep.
					$$arefData[$i]{TimeM}.$colSep.
					$$arefData[$i]{TimeC}.$colSep.
					$$arefData[$i]{Attr}.$colSep.
					$$arefData[$i]{Size}.$colSep
				):
				(
					TimeToString(hex($$arefData[$i]{TimeA})).$colSep.
					TimeToString(hex($$arefData[$i]{TimeM})).$colSep.
					TimeToString(hex($$arefData[$i]{TimeC})).$colSep.
					Win32AttribsToString(hex($$arefData[$i]{Attr})).$colSep.
					sprintf ("%015s", IntToHex($$arefData[$i]{Size})).$colSep
				)
			).
			$$arefData[$i]{ElFull}.
			"\n";
	}

	print FOUT "\n";
	print FOUT "#"."-" x $screenWidth."\n";

	close FOUT;

	print "\n".("=" x $screenWidth)."\n\n";
	print ">> Created MD5 sig file $dataFileOUT\n";

	return 0;
}


#############################################################################
# Dump outputs to a more differents file
#############################################################################
sub CreateAltDatFile {
	my ($arefHash) = @_;

	my $path       = $arefHash->{Path};
	my $filePrefix = $arefHash->{Prefix};
	my $arefData   = $arefHash->{Data};
	my $foundFiles = $arefHash->{foundFiles};
	my $foundDirs  = $arefHash->{foundDirs};
	my $foundBad   = $arefHash->{foundBad};
	my $foundBytes = $arefHash->{foundBytes};

	$path =~ s/\\/\//g;
	my $dataFileOUT = "$filePrefix.alt.md5";

	if (! open (FOUT, ">".$dataFileOUT)) {
		print "\nCannot open $dataFileOUT, exiting\n";
		exit(255);
	}
	binmode FOUT;

	for (my $i = 0; $i < scalar (@$arefData); $i++) {
		print FOUT "".
			$$arefData[$i]{SigStr}.$colSep.
			($BINARY_PRINT ?
				(
					$$arefData[$i]{Size}.$colSep
				):
				(
					sprintf ("%015s", IntToHex($$arefData[$i]{Size})).$colSep
				)
			).
			$$arefData[$i]{ElFull}.
			"\n";
	}

	close FOUT;

	print "\n".("=" x $screenWidth)."\n\n";
	print ">> Created MD5 sig file $dataFileOUT\n";

	return 0;
}


#############################################################################
#
#############################################################################
sub CompareDataFiles {
	my ($argvRef) = @_;

	my $localStartTime = time();

	my $FileL = @{$argvRef}[0];
	$FileL =~ s/\\/\//g;
	my $FileR = @{$argvRef}[1];
	$FileR =~ s/\\/\//g;

	my @DataL = ();
	my @DataR = ();
	my @SortedSigsL = ();
	my @SortedSigsR = ();
	my @SortedNamesL = ();
	my @SortedNamesR = ();

	print "\n"."-" x $screenWidth."\n";
	print "\n>> Comparing Data Files\n\n";

	print "-" x $screenWidth."\n";
	PreProcessDatFile("L", $FileL, \@DataL, \@SortedSigsL, \@SortedNamesL);

	print "-" x $screenWidth."\n";
	PreProcessDatFile("R", $FileR, \@DataR, \@SortedSigsR, \@SortedNamesR);

	CompareByFullNames  (\@SortedNamesL, \@SortedNamesR); # Cross checks files of the same FULL name
	DetailedCompare (\@SortedSigsL,  \@SortedSigsR );  # Cross checks other files

	my $CmpNameL = $FileL; $CmpNameL =~ s/^.*\/([^\/]*)$/$1/; $CmpNameL =~ s/^(.*)\.([^\.]*)$/$1/; $CmpNameL =~ s/^treehash[-_]//i;
	my $CmpNameR = $FileR; $CmpNameR =~ s/^.*\/([^\/]*)$/$1/; $CmpNameR =~ s/^(.*)\.([^\.]*)$/$1/; $CmpNameR =~ s/^treehash[-_]//i;

	my $reportName = "treehash-cmp.$CmpNameL\__$CmpNameR.txt";
	CreateCompareReport($reportName, \@SortedNamesL, \@SortedNamesR); # Produce a report

	#########################################################################
	# Report and exit
	#########################################################################

	my $elapsedTime = time()-$localStartTime+0.000001; # Strange output without slight twiddle factor here
	my $hours = int($elapsedTime/(60*60));
	my $mins  = int((($elapsedTime)/(60*60)-$hours)*60);
	my $secs  = int(((($elapsedTime)/(60*60)-$hours)*60-$mins)*60);
	my $elapsedTimeFmt = sprintf("%d:%02d:%02d", $hours, $mins, $secs);

	print "=" x $screenWidth."\n";
	print ">>>\n";
	print ">>> Elapsed time: $elapsedTimeFmt\n";
	print ">>>\n";
	print "=" x $screenWidth."\n";
	print "\n";

	return 0;
}


##############################################################################
# Create comparison report
##############################################################################
sub CreateCompareReport {
	my ($ReportFile, $DataL, $DataR) = @_;

	print "-" x $screenWidth."\n";
	print ">> Creating report $ReportFile\n\n";

	if (! open (FOUT, ">".$ReportFile)) {
		print "\nCannot open $ReportFile, exiting\n";
		exit(255);
	}
	binmode FOUT;

	foreach my $side ("L", "R") {
		my $aData;
		if ($side =~ /L/) { $aData = $DataL; }
		else              { $aData = $DataR; }
		foreach my $aref (@$aData) {
			if ($aref->{SigStr} =~ /^[-]+$/) { next; }

			my $sig_n_size   = "$aref->{SigStr}\_$aref->{Size}";
			my $this_locname = "$aref->{MyLoc}\t$aref->{ElFull}";

			if    ($aref->{Match} == M_NONE) {
				print FOUT "".Printable_const_M($aref->{Match})."\t[$sig_n_size]\t$this_locname\n";
			}
			else {
				my $that_locname = "$aref->{MatchRef}->{MyLoc}\t$aref->{MatchRef}->{ElFull}";
				my $extra_info = "";
				if ($DEBUG) { $extra_info .= "\t($aref->{MatchRef}->{MatchLoc})"; }
				print FOUT "".Printable_const_M($aref->{Match})."\t[$sig_n_size]\t$this_locname\t$that_locname"."$extra_info"."\n";
			}
		}
	}

	close FOUT;

	return 0;
}


##############################################################################
#
##############################################################################
sub CompareBySigs {
	my ($SortedSigsL, $SortedSigsR) = @_;

	print "-" x $screenWidth."\n";
	print ">> Comparing by signatures\n\n";

	foreach my $lRef (@$SortedSigsL) {
		if ($lRef->{SigStr} =~ /^[-]+$/) { next; }
		foreach my $rRef (@$SortedSigsR) {
			if ($rRef->{SigStr} =~ /^[-]+$/) { next; }
			if (($lRef->{ElFull} eq $rRef->{ElFull}) &&
				($lRef->{SigStr} eq $rRef->{SigStr}) &&
				($lRef->{Size}   eq $rRef->{Size})) {
				$lRef->{Match} = M_SFSD;
				$rRef->{Match} = M_SFSD;
				$lRef->{MatchLoc} = "R";
				$rRef->{MatchLoc} = "L";
				$lRef->{MatchRef} = $rRef;
				$rRef->{MatchRef} = $lRef;
				last;
			}
		}
	}

	return 0;
}


##############################################################################
#
##############################################################################
sub CompareByFullNames {
	my ($SortedNamesL, $SortedNamesR) = @_;

	print "-" x $screenWidth."\n";
	print ">> Comparing by full names\n\n";

	foreach my $lRef (@$SortedNamesL) {
		if ($lRef->{SigStr} =~ /^[-]+$/) { next; }
 		foreach my $rRef (@$SortedNamesR) {
			if ($rRef->{SigStr} =~ /^[-]+$/) { next; }
			if ($lRef->{ElFull} eq $rRef->{ElFull}) {
				$lRef->{Match} = M_SFDD; # This will change if md5 and size match
				$rRef->{Match} = M_SFDD; # This will change if md5 and size match
				$lRef->{MatchLoc} = "R";
				$rRef->{MatchLoc} = "L";
				$lRef->{MatchRef} = $rRef;
				$rRef->{MatchRef} = $lRef;
				if ($lRef->{SigStr}.$lRef->{Size} eq $rRef->{SigStr}.$rRef->{Size} ) { # Different sizes would invalidate MD5 results
					$lRef->{Match} = M_SFSD;
					$rRef->{Match} = M_SFSD;
				}
				last; # break out of this for loop since we found a matching name
			}
		}
	}

	return 0;
}


##############################################################################
#
##############################################################################
sub DetailedCompare {
	my ($SortedSigsL, $SortedSigsR) = @_;

	print "-" x $screenWidth."\n";
	print ">> Comparing by detailed analysis\n\n";

	my %IdentHash = ();

	#########################################################################
	# Group things together by uniqueness (MD5 and size)
	#########################################################################


	print ">> Grouping by md5 for compare\n";
	foreach my $aRef ($SortedSigsL, $SortedSigsR) {
		print ">> Block processing ".($aRef == $SortedSigsL ? "Left":"Right")."\n";
		my $side = ($aRef == $SortedSigsL ? "L":"R");
		foreach my $hRef (@$aRef) {
			my $identKey = $hRef->{SigStr}."_".$hRef->{Size};
			push @{$IdentHash{$identKey}}, [$side, $hRef];
		}
	}
	print "\n";

	#########################################################################
	# Annotate things by how unique they are
	# Find all cross-identical
	# Pick a parent for each side using algorithm:
	#   First cross-identical, first cross-same name, or first cross-same ID
	# Remainder are duped against their side's "parent"
	#########################################################################

	foreach my $identKey (sort keys %IdentHash) {
		if ($identKey =~ /^[-]/) { next; } # ignore dirs
		my $aRef = $IdentHash{$identKey};

		if (scalar @{$aRef} == 1) {
			next; # singletons ignored here since they never matched anything
		}

		my @idRefL = ();
		my @idRefR = ();
		foreach my $gRef (@{$aRef}) { # within a group
			if ($DEBUG) { print "Matches: $identKey [@$gRef[0]] ".@$gRef[1]->{ElFull}."\n"; }
			if (@$gRef[0] =~ /L/) {
				push @idRefL, @$gRef[1];
			}
			else {
				push @idRefR, @$gRef[1];
			}
		}
		if ($DEBUG) { print "\n"; }

		# Execute side-to-side cross-checks
		foreach my $lRef (@idRefL) {
			foreach my $rRef (@idRefR) {
				if    ($lRef->{ElFull} eq $rRef->{ElFull}) {
					if ($DEBUG) { print "Full match! $lRef->{ElFull}\n"; }
					# This is redundant if CompareByFullNames is already done... but it doesn't work alone.
				}
				elsif ($lRef->{ElName} eq $rRef->{ElName}) {
					if ($DEBUG) { print " Same name! $lRef->{ElFull}  vs  $rRef->{ElFull}\n"; }
					if ($lRef->{Match} ne M_SFSD && $lRef->{Match} ne M_SFDD) {
						$lRef->{Match}    = M_SNSD;
						$lRef->{MatchLoc} = "R";
						$lRef->{MatchRef} = $rRef;
					}
					if ($rRef->{Match} ne M_SFSD && $rRef->{Match} ne M_SFDD) {
						$rRef->{Match}    = M_SNSD;
						$rRef->{MatchLoc} = "L";
						$rRef->{MatchRef} = $lRef;
					}
				}
				else {
					if ($DEBUG) { print "  Just dup! $lRef->{ElFull}  vs  $rRef->{ElFull}\n"; }
					$lRef->{Match}    = M_DNSD;
					$rRef->{Match}    = M_DNSD;
					$lRef->{MatchLoc} = "R";
					$rRef->{MatchLoc} = "L";
					$lRef->{MatchRef} = $rRef;
					$rRef->{MatchRef} = $lRef;
				}
			}
		}

		# Execute intra-side cross-check (looking for dups within each side)
		foreach my $lRef (@idRefL) {
			foreach my $xRef (@idRefL) {
				if ($xRef->{ElFull} eq $lRef->{ElFull}) { next; } # It's just silly otherwise
				if    ($xRef->{ElName} eq $lRef->{ElName}) {
					if ($DEBUG) { print " Same name! $xRef->{ElFull}  vs  $lRef->{ElFull}\n"; }
					if ($xRef->{MatchLoc} ne "R") { # Cross-refs take precedence
						$xRef->{Match} = M_SNSD;
						$xRef->{MatchLoc} = "L";
						$xRef->{MatchRef} = $lRef;
					}
				}
				else {
					if ($DEBUG) { print "  Just dup! $xRef->{ElFull}  vs  $lRef->{ElFull}\n"; }
					if ($xRef->{MatchLoc} ne "R") { # Cross-refs take precedence
						$xRef->{Match} = M_DNSD;
						$xRef->{MatchLoc} = "L";
						$xRef->{MatchRef} = $lRef;
					}
				}
			}
		}

		foreach my $rRef (@idRefR) {
			foreach my $xRef (@idRefR) {
				if ($xRef->{ElFull} eq $rRef->{ElFull}) { next; } # It's just silly otherwise
				if    ($xRef->{ElName} eq $rRef->{ElName}) {
					if ($DEBUG) { print " Same name! $xRef->{ElFull}  vs  $rRef->{ElFull}\n"; }
					if ($xRef->{MatchLoc} ne "L") { # Cross-refs take precedence
						$xRef->{Match} = M_SNSD;
						$xRef->{MatchLoc} = "R";
						$xRef->{MatchRef} = $rRef;
					}
				}
				else {
					if ($DEBUG) { print "  Just dup! $xRef->{ElFull}  vs  $rRef->{ElFull}\n"; }
					if ($xRef->{MatchLoc} ne "L") { # Cross-refs take precedence
						$xRef->{Match} = M_DNSD;
						$xRef->{MatchLoc} = "R";
						$xRef->{MatchRef} = $rRef;
					}
				}
			}
		}

		if ($DEBUG) { print "\n"; }
	}

	if ($DEBUG) { print "\n\n"; }

	return 0;
}


#############################################################################
#
#############################################################################
sub FmtInt {
	my ($BytesFmt) = @_;
	$BytesFmt =~ s/(^[-+]?\d+?(?=(?>(?:\d{3})+)(?!\d))|\G\d{3}(?=\d))/$1,/g;
	return $BytesFmt;
}


#############################################################################
#
#############################################################################
sub ManglePath {
	my ($mangled) = @_;

	$mangled =~ s/:/\$/g;
	$mangled =~ s/\//_/g;
	if ($mangled eq ".") {
		$mangled = "_";
	}

	return $mangled;
}


#############################################################################
#
#############################################################################
sub GetFileAttributes {
	my ($FileName) = @_;

	# Get Unix-style attributes, mainly to get time info (many items here are unused)
	# Size > 2GB works in Perl 5.8!  So does "-s".
	my ($devStat, $inoStat, $modeStat, $nlinkStat, $uidStat, $gidStat, $rdevStat,
		$sizeStat, $atimeStat, $mtimeStat, $ctimeStat, $blksizeStat, $blocksStat) = stat $FileName;

	# Note: use caution with FILE_REPARSE_POINT.. if you see that for a given folder do NOT recurse into it
	#    SetAttributes($filename, $attribs);

	# Get Windows-style attributes (*IGNORE THE ARCHIVE BIT!*)
	my $w32Attr = INVALID_FILEATTRIBS;
	if (!GetAttributes($FileName, $w32Attr)) {
		$w32Attr = INVALID_FILEATTRIBS;
		print "\n!! Error: Cannot get Win32 attribs for $FileName\n\n";
	}

	return ($sizeStat, $atimeStat, $mtimeStat, $ctimeStat, $w32Attr);
}


#############################################################################
# Int to Hex
#############################################################################
sub IntToHex {
	my ($intVal) = @_;
	my $TEMP = Math::BigInt->new($intVal);
	my $hexVal = $TEMP->as_hex();
	$hexVal =~ s/^[0x]+//g;
	$hexVal = "0" if ($hexVal eq "");
	return $hexVal;
}


#############################################################################
# (IntLo, IntHi) to BigInt
#############################################################################
sub IntLoHiToBigInt {
	my ($intLo, $intHi) = @_;
	my $largenum = Math::BigInt->new($intHi);
	$largenum = Math::BigInt->new($intHi) * Math::BigInt->new("0x100000000") + $intLo;
	return ($largenum);
}


#############################################################################
# BigInt to (IntLo, IntHi)
#############################################################################
sub BigIntToIntLoHi {
	my ($intVal) = @_;
	my $largenum = Math::BigInt->new($intVal);
	my $hi = $largenum >> 32;
	my $lo = $largenum - $hi * Math::BigInt->new("0x100000000");
	return ($lo, $hi);
}


#############################################################################
# Hex to BigInt
#############################################################################
sub HexToInt {
	my ($hexVal) = @_;
	$hexVal =~ s/^0x//;
	my $intVal = Math::BigInt->new("0x$hexVal");
	return $intVal;
}


#############################################################################
#
#############################################################################

sub TimeToString {
	my ($inTime) = @_;
	my ($sc, $mn, $hr, $da, $mo, $yr, $wda, $yda, $dst) = localtime($inTime);
	$yr += 1900;
	$mo ++;

	return sprintf("%04d-%02d-%02d.%02d:%02d:%02d", $yr, $mo, $da, $hr, $mn, $sc);
}


#############################################################################
#
#############################################################################
sub findElements {
	my ($SRCROOT, $aref) = @_;

	my $foundDirs   = 0;
	my $foundFiles  = 0;
	my $foundBad    = 0;

	my $matchPath = quotemeta($SRCROOT);

	# Define the search routine
	# This construction resolves warnings of the form
	#    "Variable "$aref" will not stay shared at..."
	# for variables within the search routine
    my $process_file = sub { # Anonymous sub for local use here
		my $curElem = $_;
		my $curDir  = $File::Find::dir."/";
		my $curRelName = $File::Find::name;

		if ($curElem eq "." || $curElem eq "..") { return; }

		my $elementShort = $curRelName;
		$elementShort =~ s/^($matchPath)//;
		$elementShort =~ s/^\///g; # Gets rid of any initial '/'
		$elementShort =~ s/\/$//g; # Gets rid of any trailing '/'

		if (-d $curElem) {
			if (IsIgnoredElement($elementShort, \@IgnoredFolders)) {
				print ">>> SKIP DIR:  $elementShort\n"; 
				$File::Find::prune = 1;
				return;
			}
		}
		else {
			if (IsIgnoredElement($elementShort, \@IgnoredFiles)) {
				print ">>> SKIP FILE: $elementShort\n";
				return;
			} # Never prune for non-folders
		}

		if (!-e $curElem) { $foundBad++; print "\n!! Error: Element DNE: $curElem\n"; return; }
		push @$aref, $curRelName;
		(-d $curElem) ? ($foundDirs++) : ($foundFiles++);
	};

	# Run the search
	find(\&$process_file, $SRCROOT);

	return ($foundFiles, $foundDirs, $foundBad);
}


#############################################################################
#
#############################################################################

sub GetMD5Sig {
	# 128 bits packed into 32 hex digits
	# i.e., 96d98bdd4322b06289a84b3ab0f200ad

	my ($inFile, $processing_mode) = @_;

	my $readBytes = 0;

	if (!defined $processing_mode) {
		$processing_mode = "";
	}

	use Digest::MD5;

	#my $sigData = "";
	my $sigHexString = "?" x 32; # We should never actually see this!
	#my $sigSize = -1; # Bytes in sig: -1 = not set or error, 0 = not applicable, 16 = MD5 or similar

	if (-f $inFile) {
		my $rc = open(FILE, $inFile);
		if ($rc) {
			if ($processing_mode eq "mp3") {
				my $md5 = Digest::MD5->new;
				my $bindata = "";
				my $buffer = "";
				binmode(FILE);

				my $origBytes = (-s $inFile);
		
				my $ID3v2_ID    = "ID3";
				my $ID3v2_VER   = 0xFF;
				my $ID3v2_REV   = 0xFF;
				my $ID3v2_FLAGS = 0;
				my $ID3v2_SIZE  = 0;
				my $ID3v2_BLOCK = "";

				while(!eof(FILE)){
					my $curOffset = tell FILE;
					my $readLength = 10;
					if ($curOffset != 0) { $readLength = 1024*1024; }
					read FILE, $buffer, $readLength;
					if ($curOffset == 0 && $buffer =~ /^$ID3v2_ID/) {
						my @bufferArray = split //, $buffer;
						$ID3v2_VER   = ord($bufferArray[3]);
						$ID3v2_REV   = ord($bufferArray[4]);
						$ID3v2_FLAGS = ord($bufferArray[5]);
						$ID3v2_SIZE  = ord($bufferArray[6])*0x80*0x80*0x80+
									   ord($bufferArray[7])*0x80*0x80+
									   ord($bufferArray[8])*0x80+
									   ord($bufferArray[9]);
						if ($DEBUG) {
							print "\nMP3: Found $ID3v2_ID"."v2.$ID3v2_VER.$ID3v2_REV header (".
								  "flags = 0b".unpack("B8", pack("N", $ID3v2_FLAGS)).", ".
								  "size = 0x".unpack("H8", pack("N", $ID3v2_SIZE)).
								  "( ".sprintf("%d", $ID3v2_SIZE)." bytes)".
								  ") at offset $curOffset - $inFile\n";
						}
						$ID3v2_BLOCK .= $buffer;
						read FILE, $buffer, $ID3v2_SIZE; # Eat the rest of this ID3 block
						$ID3v2_BLOCK .= $buffer;
					}
					else {
						$bindata .= $buffer;
					}
				}
				close FILE;

				# Scan for "APETAGEX"
				my $matchStr = "APETAGEX";
				my $result = 0;
				my @results = ();
				my @resultsEndoff = ();
				do {
					$result = index($bindata, $matchStr, $result);
					if ($result >= 0) {
						push @results, $result;
						push @resultsEndoff, ($result - length($bindata)); # Special end-offset results
						$result++;
					}
				} while ($result >= 0);
				if (scalar @results > 0) {
					print "\nWarning: MP3: \"$matchStr\" found at end offset ".join(", ", @resultsEndoff)." - $inFile\n";
					$bindata = substr($bindata, 0, $results[0]); # Trim the tail from the first instance of an APETAG
				}

				# TAG appears to come after APETAGs
				my $bindataTail = substr($bindata, length($bindata)-128, 128);
				if ($bindataTail =~ /^TAG/) {
					if ($DEBUG) {
						print "\nMP3: TAG found, stripping - $inFile\n";
					}
					$bindata = substr($bindata, 0, length($bindata)-128);
				}
				
			    $readBytes = length($bindata); # The actual amount of stripped audio data read
				if ($DEBUG) { print "\nRead $readBytes data bytes out of $origBytes total bytes - $inFile\n"; }
				if ($readBytes/$origBytes < 0.90) {
					print "\nWarning: MP3: >10\% missing data - $readBytes << $origBytes - $inFile\n";
				}
				$md5->add($bindata);
				$sigHexString = $md5->hexdigest;

				##################################################################################
				#   # Dump the core music data for examination
				#	my $fout = "$inFile.coredata";
				#	if ($fout ne "") {	
				#		open (FOUT, ">$fout") or die "Cannot open $fout : $!\n";
				#		binmode FOUT;
				#		print FOUT $ID3v2_BLOCK; # To preserve the ID3v2 block
			    #		print FOUT $bindata; # For verification
				#		close FOUT;
				#	}
				##################################################################################
			}
			##################################################################################
			#	# Preliminary/testing:
			#	# CPAN MPEG-Audio-Frame (special mod one) needed for MP3 activity
			#	# CPAN Audio-Digest-MP3-0.1 needed for MP3 activity
			#	elsif ($processing_mode eq "mp3OLD") {
			#		use MPEG::Audio::Frame; # For MP3 data-block decapsulation
			#		use Audio::Digest::MP3; # For MP3 digesting
			#		binmode(FILE);
			#		my $md5 = Digest::MD5->new;
			#		while(my $frame = MPEG::Audio::Frame->read(\*FILE)){
			#		    $md5->add($frame->asbin);
			#		    $readBytes += length($frame->asbin);
			#		}
			#		$sigHexString = $md5->hexdigest;
			#	}
			##################################################################################
			else { # normal file
				binmode(FILE);
				$sigHexString = Digest::MD5->new->addfile(*FILE)->hexdigest;
				$readBytes = (-s $inFile);
				# $sigHexString = "aBBa3445aBBa3445aBBa3445aBBa3445";
				# $sigData = pack "H*", $sigHexString;
			}
			close (FILE);
		}
		else {
			print "\n!! Cannot open $inFile: $!\n";
			#$sigSize = -1;
			$sigHexString = "?" x 32;
		}
	}
	elsif (-d $inFile) {
		#$sigSize = 0;
		$sigHexString = "-" x 32;
	}
	else {
		print "\n!! Unhandled file type for $inFile\n";
		#$sigSize = -1;
		$sigHexString = "?" x 32;
	}

	return ($sigHexString, $readBytes);
}


##############################################################################
#
##############################################################################
sub PreProcessDatFile {
	my ($myLoc, $theRoot, $arefData, $arefSortedSigs, $arefSortedNames) = @_;

	my @DataFiles   = ();
	my $foundBytes  = 0;
	my $foundDirs   = 0;
	my $foundFiles  = 0;
	my $foundBad    = 0;


	#########################################################################
	if (-d $theRoot) {
		foreach(`cmd /c dir /b \"$theRoot\"`) {
			chomp;
			push @DataFiles, "$theRoot\\$_";
		}
	}
	elsif (-f $theRoot) {
		push @DataFiles, $theRoot;
	}
	else {
		print "\n$theRoot DNE, exiting\n";
		exit(255);
	}

	#########################################################################
	foreach (@DataFiles) {
		chomp;
		print ">> Processing $myLoc: $_\n";

		if (! open (FIN, "$_")) {
			print "\nCannot open $_, exiting\n";
			exit(255);
		}
		binmode FIN;

		my $BasePath = "UNDEFINED";

		foreach (<FIN>) {
			chomp;
			if (/^\s*\#\s*BASE PATH: (.*)$/i) {
				$BasePath = $1;
				$BasePath =~ s/\\/\//g;
				$BasePath =~ s/\/$//g;
				next;
			}
			elsif (/^\s*\#/ || /^\s*$/) {
				next;
			}

			my $curLine = $_;
			my @fields = split /;/, $curLine, 7;
			my $elPath = "";
			my $elName = $fields[6];
			my $elementShort = $elName;

			# Used to perform an IsIgnoredElement() check here (deprecated)

			if ($elName =~ /\/ /) {
				print "WEIRD!  $elName\n";
				$elName =~ s/\/ /\//g;
			}

			if ($elName =~ /^(.*)\/([^\/]*)$/) {
				$elPath = $1;
				$elName = $2;
			}

			my %data = (  # For a given element
				SigType  => (($fields[0] =~ /^[a-f\d]+$/i)?1:0),
				SigSize  => (($fields[0] =~ /^[a-f\d]+$/i)?(length($fields[0])/2):0),
				SigData  => (($fields[0] =~ /^[a-f\d]+$/i)?(pack "H*", $fields[0]):""),
				SigStr   => $fields[0],  # Will use this as a string in comparisons
				TimeA    => $fields[1],
				TimeM    => $fields[2],
				TimeC    => $fields[3],
				Attr     => $fields[4],
				Size     => $fields[5],  # Will use this as a string in comparisons
				ElPath   => $elPath,
				ElName   => $elName,
				ElFull   => $elementShort,
				ElType   => T_NONE,
				Match    => M_NONE, # No matches to start off with
				MatchLoc => "", # If I have a match, where is it? (opposites should have precedence)
				MatchRef => [], # If I have a match, what is it?
				MyLoc    => $myLoc, # To which side do *I* belong?
			);

			push @$arefData, \%data;

			if ($fields[0] =~ /^[-]+$/) { $foundDirs++; }
			else { $foundFiles++; }

			my $fileSize = HexToInt($fields[5]);
			$foundBytes += $fileSize;
		}

		close FIN;
	}

	print ">> Found: $foundFiles file(s), $foundDirs folder(s) comprising ".(FmtInt($foundBytes))." bytes\n";


	#########################################################################

	for(sort { $a->{SigStr} cmp $b->{SigStr} } @$arefData) {
		push @$arefSortedSigs, $_;
	}

	for(sort { $a->{ElFull} cmp $b->{ElFull} } @$arefData) {
		push @$arefSortedNames, $_;
	}

	if ($DEBUG) {
		open FILE, ">$myLoc-data.log" or die "\n!! Error: Cannot create log $myLoc-data.log\n\n";
		foreach (@$arefData) {
			print FILE "".sprintf("%s;%02x;%s;%s;%s\n", $_->{SigStr}, $_->{Attr}, $_->{Size}, $_->{ElPath}, $_->{ElName});
		}
		close FILE;

		open FILE, ">$myLoc-sigs.log" or die "\n!! Error: Cannot create log $myLoc-sigs.log\n\n";
		foreach (@$arefSortedSigs) {
			print FILE "".sprintf("%s;%02x;%s;%s;%s\n", $_->{SigStr}, $_->{Attr}, $_->{Size}, $_->{ElPath}, $_->{ElName});
		}
		close FILE;

		open FILE, ">$myLoc-names.log" or die "\n!! Error: Cannot create log $myLoc-names.log\n\n";
		foreach (@$arefSortedNames) {
			print FILE "".sprintf("%s;%02x;%s;%s;%s\n", $_->{SigStr}, $_->{Attr}, $_->{Size}, $_->{ElPath}, $_->{ElName});
		}
		close FILE;
	}

	print "\n";

	return 0;
}


##############################################################################
#
##############################################################################
sub Deflatus {
	my ($infile, $outfile, $startPos, $deflationlevel) = @_;

	open FIN, "$infile" or die "Cannot open $infile\n";
	binmode FIN;
	open FOUT, "+<$outfile" or die "Cannot open $outfile\n"; # Open for database-style updating
	binmode FOUT;

	if (!seek(FOUT, $startPos, 0)) { print "seek failed\n"; }

	my $x = deflateInit(-Level => $deflationlevel) or die "Cannot create a deflation stream\n";

	my $inputBytes = 0;
	my $outputBytes = 0;
	my $input = '';
	my ($output, $status);
	while (read(FIN, $input, DEFAULT_FILEIO_CHUNK_SIZE)) {
		$inputBytes += length($input);
		($output, $status) = $x->deflate(\$input);
		$outputBytes += length($output);
		$status == Z_OK or die "deflation failed\n";
		print FOUT $output;
	}

	($output, $status) = $x->flush();
	$outputBytes += length($output);

	$status == Z_OK	or die "deflation failed\n";

	print FOUT $output;

	close FOUT;
	close FIN;

	print "Deflated: $inputBytes to $outputBytes (".sprintf("%6.2f", $outputBytes/$inputBytes*100.0)."\%) starting at $startPos\n";

	return $outputBytes;
}


##############################################################################
#
##############################################################################
sub Inflatus {
	my ($infile, $outfile, $startPos, $maxIn) = @_;

	open FIN, "$infile" or die "Cannot open $infile\n";
	binmode FIN;
	open FOUT, ">$outfile" or die "Cannot open $outfile\n";
	binmode FOUT;

	if (!seek(FIN, $startPos, 0)) { print "seek failed\n"; }

	my $x = inflateInit() or die "Cannot create a inflation stream\n";

	my $inputBytes = 0;
	my $outputBytes = 0;
	my $input = '';
	my ($output, $status);
	my $readSize = DEFAULT_FILEIO_CHUNK_SIZE;
	if ($readSize > $maxIn) { $readSize = $maxIn; }
	my $FINALPASS = 0;

	while (read(FIN, $input, $readSize)) {
		$inputBytes += length($input);
		if ($inputBytes + $readSize > $maxIn) { $readSize = $maxIn - $inputBytes; }
		if ($inputBytes == $maxIn) { $FINALPASS = 1; }
		($output, $status) = $x->inflate(\$input);
		$outputBytes += length($output);
		print FOUT $output if $status == Z_OK or $status == Z_STREAM_END;
		last if $status != Z_OK;
		last if $FINALPASS;
	}

	$status == Z_STREAM_END or die "inflation failed\n";

	close FOUT;
	close FIN;

	print "Inflated: $inputBytes to $outputBytes (".sprintf("%6.2f", $outputBytes/$inputBytes*100.0)."\%) starting at $startPos\n";

	return 0;
}

#----------------------------------------------------------------------------#

