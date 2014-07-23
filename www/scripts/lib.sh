#!/bin/sh

#========================
#MAGIC CONSTANTS
#========================

MAX_TILE=50
if [ "$DEBUG" ]
then
	WGET='wget'
else
	WGET='wget -q'
fi

#========================
#HELPER FUNCTIONS
#========================

#Utility functions
function max()
{
	local MAX=$1
	shift
	
	for CANDIDATE in $#
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
	
	for CANDIDATE in $#
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
	if [ $# -ne 5 ]
	then
		echo "Usage: $0 urlGenerator fileGenerator pageId zoom outputDir"
		exit 1
	fi
	
	local WGET_HTTP_ERROR=8
	local MIN_TILE_SIZE=`expr 1024 '*' 5` #5.0 kilobytes
	
	local URL_GENERATOR=$1
	local FILE_GENERATOR=$2
	local PAGE_ID=$3
	local TILE_Z=$4
	local OUTPUT_DIR=$5
	local OUTPUT_FILE=$OUTPUT_DIR/$PAGE_ID.bmp
	local TMP_DIR=$OUTPUT_DIR/tmp
	
	local MAX_TILE_X=$MAX_TILE
	local MAX_TILE_Y=$MAX_TILE
	
	mkdir -p "$TMP_DIR"
	for TILE_X in `seq 0 $MAX_TILE_X`
	do
		local TILE_Y=0
		local TILE_FILE="$TMP_DIR/`$FILE_GENERATOR $TILE_X $TILE_Y`.jpg"
		$WGET `$URL_GENERATOR $PAGE_ID $TILE_X $TILE_Y $TILE_Z` -O $TILE_FILE
		if [ \
			\( $? == "$WGET_HTTP_ERROR" \) -o \
			\( `stat --format=%s $TILE_FILE` -lt $MIN_TILE_SIZE \) \
		]
		then
			rm -f $TILE_FILE
			MAX_TILE_X=`expr $TILE_X - 1`
			break
		fi
	
		for TILE_Y in `seq 0 $MAX_TILE_Y`
		do
			local TILE_FILE="$TMP_DIR/`$FILE_GENERATOR $TILE_X $TILE_Y`.jpg"
			$WGET `$URL_GENERATOR $PAGE_ID $TILE_X $TILE_Y $TILE_Z` -O $TILE_FILE
				
			if [ \
				\( $? == "$WGET_HTTP_ERROR" \) -o \
				\( `stat --format=%s $TILE_FILE` -lt $MIN_TILE_SIZE \) \
			]
			then
				rm -f $TILE_FILE
				MAX_TILE_Y=`expr $TILE_Y - 1`
				break
			fi
		done;
	done;
	
	montage $TMP_DIR/* -mode Concatenate -tile `expr $MAX_TILE_X + 1`x`expr $MAX_TILE_Y + 1` $OUTPUT_FILE
	convert $OUTPUT_FILE -trim $OUTPUT_FILE

	rm -rf $TMP_DIR
}

#========================
#LIBRARY DEPENDENT FUNCTIONS
#========================

function rsl()
{
	if [ $# -ne 1 ]
	then
		echo "Usage: $0 book_id"
		exit 1
	fi
	
	local BOOK_ID=$1
	
	$WGET "http://dlib.rsl.ru/loader/view/$1?get=pdf" -O "rsl.$BOOK_ID.pdf"
}

function haithi()
{
	if [ $# -ne 2 ]
	then
		echo "Usage: $0 book_id page_count"
		exit 1
	fi
	
	local BOOK_ID=$1
	local PAGE_COUNT=$2
	local OUTPUT_DIR="haithi.$BOOK_ID"
	
	mkdir -p "$OUTPUT_DIR"
	for PAGE in `seq 1 $PAGE_COUNT`
	do
		while ( \
			$WGET "http://babel.hathitrust.org/cgi/imgsrv/image?id=$BOOK_ID;seq=$PAGE;width=1000000" -O "$OUTPUT_DIR/`printf %04d.jpg $PAGE`"; \
			[ "$?" == "$WGET_HTTP_ERROR" ] \
		)
		do
			sleep 30
		done;
	done;
}

function gallicaTileFile()
{
	if [ $# -ne 2 ]
	then
		echo "Usage: $0 x y"
		exit 1
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
		exit 1
	fi
	
	local BOOK_ID=$1
	local TILE_X=$2
	local TILE_Y=$3
	local TILE_Z=$4
	local TILE_SIZE=2048
	
	local LEFT=`expr $TILE_X '*' $TILE_SIZE`
	local TOP=`expr $TILE_Y '*' $TILE_SIZE`
	
	echo "http://gallica.bnf.fr/proxy?method=R&ark=$BOOK_ID.f1&l=$TILE_Z&r=$TOP,$LEFT,$TILE_SIZE,$TILE_SIZE"
}

function dusseldorfTileFile()
{
	if [ $# -ne 2 ]
	then
		echo "Usage: $0 x y"
		exit 1
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
		exit 1
	fi
	
	local IMAGE_ID=$1
	local TILE_X=$2
	local TILE_Y=$3
	local TILE_Z=$4
	
	#some unknown number with unspecified purpose
	local UNKNOWN_NUMBER=5089
	
	echo "http://digital.ub.uni-duesseldorf.de/image/tile/wc/nop/$UNKNOWN_NUMBER/1.0.0/$IMAGE_ID/$TILE_Z/$TILE_X/$TILE_Y.jpg"
}

function gallicaTiles()
{
	if [ $# -ne 1 ]
	then
		echo "Usage:  $0 ark_id"
		exit 1
	fi
	
	local BOOK_ID=$1
	local ZOOM=6
	local OUTPUT_DIR=.
	tiles gallicaTilesUrl gallicaTileFile $BOOK_ID $ZOOM $OUTPUT_DIR
}

function dusseldorfTiles()
{
	if [ $# -ne 1 ]
	then
		echo "Usage: $0 image_id"
		exit 1
	fi
	local BOOK_ID=$1
	local ZOOM=6
	local OUTPUT_DIR=.
	tiles dusseldorfTilesUrl dusseldorfTileFile $BOOK_ID $ZOOM $OUTPUT_DIR
}