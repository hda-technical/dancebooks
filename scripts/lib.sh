#!/bin/sh

#========================
#MAGIC CONSTANTS
#========================

MAX_TILE=50

#Latin numbers in lowercase (from 1 to 10)
LATIN_NUMBERS="i ii iii iv v vi vii viii ix x "
#Extra latin number (not used)
#"xi xii xiii xiv xv xvi xvii xviii xix xx xxi xxii xxiii xxiv xxv xxvi xxvii xxviii xxix xxx xxxi xxxii xxxiii xxxiv xxxv xxxvi xxxvii xxxviii xxxix xl"

CURL_HTTP_ERROR=22

MIN_FILE_SIZE_BYTES=1024

#========================
#HELPER FUNCTIONS
#========================


function webGet()
{
	if [ $# -ne 2 ]
	then
		echo "Usage: $0 url output_file"
		return 1
	fi

	local URL=$1
	local OUTPUT_FILE=$2

	if [ -f "$OUTPUT_FILE" ]
	then
		return 0
	fi

	echo -n "Getting $1 ... "

	curl \
		--silent \
		--fail \
		--connect-timeout 5 \
		--output "$OUTPUT_FILE" \
		"$URL" 

	if [ "$?" == "$CURL_HTTP_ERROR" ]
	then
		echo "FAIL"
		return 1
	elif [ -f "$OUTPUT_FILE" ]
	then
		if [ `stat --format=%s "$OUTPUT_FILE"` -lt "$MIN_FILE_SIZE_BYTES" ]
		then
			rm -f "$OUTPUT_FILE"
			echo "FAIL"
			return 1
		else
			echo "OK"
			return 0
		fi
	fi
}

#Utility functions
function max()
{
	local MAX=$1
	shift

	for CANDIDATE in $@
	do
		if [ "$CANDIDATE" -gt "$MAX" ]
		then
			MAX=$CANDIDATE
		fi
	done

	echo $MAX
}

function min()
{
	local MIN=$1
	shift

	for CANDIDATE in $@
	do
		if [ "$CANDIDATE" -lt "$MIN" ]
		then
			MIN=$CANDIDATE
		fi
	done

	echo $MIN
}

function tiles()
{
	if [ $# -ne 6 ]
	then
		echo "Usage: $0 urlGenerator fileGenerator pageId zoom outputDir"
		return 1
	fi

	local URL_GENERATOR=$1
	local FILE_GENERATOR=$2
	local PAGE_ID=$3
	local TILE_Z=$4
	local TILE_SIZE=$5
	local OUTPUT_DIR=$6
	local OUTPUT_FILE=$OUTPUT_DIR/$PAGE_ID.bmp
	local TMP_DIR=$OUTPUT_DIR/tmp

	local MAX_TILE_X=$MAX_TILE
	local MAX_TILE_Y=$MAX_TILE

	mkdir -p "$TMP_DIR"
	for TILE_X in `seq 0 $MAX_TILE_X`
	do
		local TILE_Y=0
		local TILE_FILE="$TMP_DIR/`$FILE_GENERATOR $TILE_X $TILE_Y`.jpg"
		webGet `$URL_GENERATOR $PAGE_ID $TILE_X $TILE_Y $TILE_Z` "$TILE_FILE"
		if [ $? -ne 0 ]
		then
			MAX_TILE_X=`expr $TILE_X - 1`
			break
		fi

		for TILE_Y in `seq 0 $MAX_TILE_Y`
		do
			local TILE_FILE="$TMP_DIR/`$FILE_GENERATOR $TILE_X $TILE_Y`.jpg"
			webGet `$URL_GENERATOR $PAGE_ID $TILE_X $TILE_Y $TILE_Z` "$TILE_FILE"

			if [ $? -ne 0 ]
			then
				MAX_TILE_Y=`expr $TILE_Y - 1`
				break
			fi
		done;
	done;

	montage \
		$TMP_DIR/* \
		-mode Concatenate \
		-geometry "${TILE_SIZE}x${TILE_SIZE}>" \
		-tile `expr $MAX_TILE_X + 1`x`expr $MAX_TILE_Y + 1` \
		$OUTPUT_FILE
	convert $OUTPUT_FILE -trim $OUTPUT_FILE
	
	rm -rf "$TMP_DIR"
}

# removes wrong symbols from filename, replacing them by underscores
function makeOutputDir()
{
	local OUTPUT_DIR=$1
	echo "$OUTPUT_DIR" | sed -e 's/[:\/\\\?\*"]/_/g'
}

#========================
#LIBRARY DEPENDENT FUNCTIONS
#========================

#========================
#Single image per page downloaders
#========================
function rsl()
{
	if [ $# -ne 1 ]
	then
		echo "Usage: $0 book_id"
		return 1
	fi

	local BOOK_ID=$1

	webGet "http://dlib.rsl.ru/loader/view/$1?get=pdf" "rsl.$BOOK_ID.pdf"
}

function hathi()
{
	if [ $# -ne 2 ]
	then
		echo "Usage: $0 book_id page_count"
		return
	fi

	local BOOK_ID=$1
	local PAGE_COUNT=$2
	local OUTPUT_DIR=`makeOutputDir "hathi.$BOOK_ID"`

	mkdir -p "$OUTPUT_DIR"
	for PAGE in `seq 1 $PAGE_COUNT`
	do
		while ( \
			webGet "http://babel.hathitrust.org/cgi/imgsrv/image?id=$BOOK_ID;seq=$PAGE;width=1000000" "$OUTPUT_DIR/`printf %04d.jpg $PAGE`"; \
			[ "$?" -ne 0 ] \
		)
		do
			sleep 30
		done;
	done;
}

function gallica()
{
	if [ $# -ne 2 ]
	then
		echo "Usage $0 ark_id page_count"
		return 1
	fi

	local BOOK_ID=$1
	local OUTPUT_DIR="gallica.$BOOK_ID"
	local PAGE_COUNT=$2
	mkdir -p "$OUTPUT_DIR"
	for PAGE in `seq $PAGE_COUNT`
	do
		local OUTPUT_FILE=`printf $OUTPUT_DIR/%04d.jpg $PAGE`
		webGet "http://gallica.bnf.fr/ark:/12148/$BOOK_ID/f$PAGE.highres" $OUTPUT_FILE
	done
}

function britishLibrary()
{
	if [ $# -ne 2 ]
	then
		echo "Usage: $0 book_id page_count"
		return 1
	fi
	
	local BOOK_ID=$1
	local OUTPUT_DIR="british.$BOOK_ID"
	local PAGE_COUNT=$2
	mkdir -p "$OUTPUT_DIR"
	for PAGE in `seq $PAGE_COUNT`
	do
		local OUTPUT_FILE=`printf $OUTPUT_DIR/%04d.jpg $PAGE`
		webGet "http://access.bl.uk/IIIFImageService/ark:/81055/${BOOK_ID}.0x`printf %06x $PAGE`/0,0,5000,5000/pct:100/0/native.jpg" "$OUTPUT_FILE"
	done
}

function vwml()
{
	if [ $# -ne 3 ]
	then
		echo "Usage: $0 book_shorthand book_id page_count"
		return 1
	fi

	local BOOK_SHORTHAND=$1
	local BOOK_ID=$2
	local PAGE_COUNT=$3
	local OUTPUT_DIR="vwml.$BOOK_ID"

	mkdir -p "$OUTPUT_DIR"
	local OUTPUT_PAGE=1

	#Getting pages with latin numeration first
	for LATIN_NUMBER in $LATIN_NUMBERS
	do
		local NORMALIZED_NUMBER=`printf %04s $LATIN_NUMBER | sed -e 's/ /0/g'`
		local OUTPUT_FILE="$OUTPUT_DIR/latin_`printf %04d $OUTPUT_PAGE`.jpg"
		webGet "http://media.vwml.org/images/web/$BOOK_SHORTHAND/$BOOK_ID$NORMALIZED_NUMBER.jpg" "$OUTPUT_FILE"
		if [ $? -ne 0 ]
		then
			break
		else
			local OUTPUT_PAGE=`expr $OUTPUT_PAGE + 1`
		fi
	done

	for PAGE in `seq 1 $PAGE_COUNT`
	do
		local OUTPUT_FILE="$OUTPUT_DIR/`printf %04d $OUTPUT_PAGE`.jpg"
		webGet "http://media.vwml.org/images/web/$BOOK_SHORTHAND/$BOOK_ID`printf %04d $PAGE`.jpg" "$OUTPUT_FILE"
		if [ $? == 0 ]
		then
			local OUTPUT_PAGE=`expr $OUTPUT_PAGE + 1`
		fi
	done
}

#========================
#Tiled page downloaders
#========================
function gallicaTileFile()
{
	if [ $# -ne 2 ]
	then
		echo "Usage: $0 x y"
		return 1
	fi

	local TILE_X=$1
	local TILE_Y=$2

	echo `printf %04d $TILE_Y`x`printf %04d $TILE_X`
}

function gallicaTilesUrl()
{
	if [ $# -ne 4 ]
	then
		echo "Usage: $0 ark_id x y z"
		return 1
	fi

	local BOOK_ID=`echo $1 | sed -e 's/\./\//g'`
	local TILE_X=$2
	local TILE_Y=$3
	local TILE_Z=$4
	local TILE_SIZE=1024

	local LEFT=`expr $TILE_X '*' $TILE_SIZE`
	local TOP=`expr $TILE_Y '*' $TILE_SIZE`

	echo "http://gallica.bnf.fr/iiif/ark:/12148/$BOOK_ID/$LEFT,$TOP,1024,1024/pct:100/0/native.jpg"
}

function gallicaTiles()
{
	if [ $# -ne 1 ]
	then
		echo "Usage: $0 ark_id"
		return 1
	fi
	
	#overriding global constant
	MIN_FILE_SIZE_BYTES=20960
	
	local BOOK_ID=$1
	local ZOOM=6
	local TILE_SIZE=1024
	local OUTPUT_DIR=.
	
	tiles gallicaTilesUrl gallicaTileFile $BOOK_ID $ZOOM $TILE_SIZE $OUTPUT_DIR
}

function dusseldorfTileFile()
{
	if [ $# -ne 2 ]
	then
		echo "Usage: $0 x y"
		return 1
	fi

	local TILE_X=$1
	local TILE_Y=$2
	#dusseldorf tiles are numbered from bottom to top
	local REAL_TILE_Y=`expr $MAX_TILE - $TILE_Y`

	echo `printf %04d $REAL_TILE_Y`x`printf %04d $TILE_X`
}

function dusseldorfTilesUrl()
{
	if [ $# -ne 4 ]
	then
		echo "Usage: $0 image_id x y z"
		return 1
	fi

	local IMAGE_ID=$1
	local TILE_X=$2
	local TILE_Y=$3
	local TILE_Z=$4

	#some unknown number with unspecified purpose
	local UNKNOWN_NUMBER=5089

	echo "http://digital.ub.uni-duesseldorf.de/image/tile/wc/nop/$UNKNOWN_NUMBER/1.0.0/$IMAGE_ID/$TILE_Z/$TILE_X/$TILE_Y.jpg"
}

function dusseldorfTiles()
{
	if [ $# -ne 1 ]
	then
		echo "Usage: $0 image_id"
		return 1
	fi
	local BOOK_ID=$1
	local ZOOM=6
	local TILE_SIZE=256
	local OUTPUT_DIR=.
	
	tiles dusseldorfTilesUrl dusseldorfTileFile $BOOK_ID $ZOOM $TILE_SIZE $OUTPUT_DIR
}

if [ $# -lt 2 ]
then
	echo "Usage: $0 grabber <grabber params>"
	exit 1
fi

GRABBER=$1
shift
$GRABBER $@
