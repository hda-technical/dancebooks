#!/bin/sh

#set -x

#========================
#MAGIC CONSTANTS
#========================

MAX_TILE_X=50
MAX_TILE_Y=50

#Latin numbers in lowercase (from 1 to 10)
LATIN_NUMBERS="i ii iii iv v vi vii viii ix x "
#Extra latin number (not used)
#"xi xii xiii xiv xv xvi xvii xviii xix xx xxi xxii xxiii xxiv xxv xxvi xxvii xxviii xxix xxx xxxi xxxii xxxiii xxxiv xxxv xxxvi xxxvii xxxviii xxxix xl"

CURL_HTTP_ERROR=22
CURL_TIMEOUT=28

MIN_FILE_SIZE_BYTES=1024

#========================
#HELPER FUNCTIONS
#========================


webGet()
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
		--retry 2 \
		--connect-timeout 3 \
		--retry-delay 2 \
		--max-time 60 \
		--output "$OUTPUT_FILE" \
		"$URL"

	local EXIT_CODE=$?

	if [ "$EXIT_CODE" -eq "$CURL_TIMEOUT" ]
	then
		echo "TIMEOUT"
		return 1
	fi
	if [ "$EXIT_CODE" -eq "$CURL_HTTP_ERROR" ]
	then
		rm -f "$OUTPUT_FILE"
		echo "HTTP ERROR"
		return 1
	fi
	if [ ! -e "$OUTPUT_FILE" ]
	then
		echo "NO OUTPUT"
		return 1
	fi

	if [ `stat --format=%s "$OUTPUT_FILE"` -lt "$MIN_FILE_SIZE_BYTES" ]
	then
		rm -f "$OUTPUT_FILE"
		echo "FILE TOO SMALL"
		return 1
	fi

	echo "OK"
	return 0
}

#Utility functions
max()
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

min()
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

roundDiv()
{
	local VAL=$1
	local DIVISOR=$2

	local RESULT=`echo "$VAL" / "$DIVISOR" | bc`
	local REST=`echo "$VAL" % "$DIVISOR" | bc`
	if [ "$REST" -eq 0 ]
	then
		echo $RESULT
	else
		echo "$RESULT" + 1 | bc
	fi
}

dullValidate()
{
	return 0
}

tiles()
{
	if [ $# -ne 7 ]
	then
		echo "Usage: $0 urlGenerator fileGenerator fileValidator pageId zoom outputDir"
		return 1
	fi

	local URL_GENERATOR=$1
	local FILE_GENERATOR=$2
	local TILE_VALIDATOR=$3
	local PAGE_ID=$4
	local TILE_Z=$5
	local TILE_SIZE=$6
	local OUTPUT_DIR=$7
	local OUTPUT_FILE="$OUTPUT_DIR/`basename $PAGE_ID`.bmp"
	local TMP_DIR="$OUTPUT_DIR/`basename $PAGE_ID`.tmp"

	local LAST_TILE_WIDTH=$TILE_SIZE
	local LAST_TILE_HEIGHT=$TILE_HEIGHT

	mkdir -p "$TMP_DIR"
	for TILE_X in `seq 0 $MAX_TILE_X`
	do
		local TILE_Y=0
		local TILE_FILE="$TMP_DIR/`$FILE_GENERATOR $TILE_X $TILE_Y`.jpg"
		webGet `$URL_GENERATOR $PAGE_ID $TILE_X $TILE_Y $TILE_Z` "$TILE_FILE" && $TILE_VALIDATOR "$TILE_FILE"
		if [ $? -ne 0 ]
		then			
			rm -f "$TILE_FILE"
			local MAX_TILE_X=`expr $TILE_X - 1`
			local LAST_TILE_FILE="$TMP_DIR/`$FILE_GENERATOR $MAX_TILE_X 0`.jpg"
			local LAST_TILE_WIDTH=`identify -format '%w' "$LAST_TILE_FILE"`
			break
		fi

		for TILE_Y in `seq 0 $MAX_TILE_Y`
		do
			local TILE_FILE="$TMP_DIR/`$FILE_GENERATOR $TILE_X $TILE_Y`.jpg"
			webGet `$URL_GENERATOR $PAGE_ID $TILE_X $TILE_Y $TILE_Z` "$TILE_FILE" && $TILE_VALIDATOR "$TILE_FILE"

			if [ $? -ne 0 ]
			then
				rm -f "$TILE_FILE"
				local MAX_TILE_Y=`expr $TILE_Y - 1`
				local LAST_TILE_FILE="$TMP_DIR/`$FILE_GENERATOR 0 $MAX_TILE_Y`.jpg"
				local LAST_TILE_HEIGHT=`identify -format '%h' "$LAST_TILE_FILE"`
				break
			fi
		done;
	done;

	if [ \
		"$MAX_TILE_X" -gt "0" -a \
		"$MAX_TILE_Y" -gt "0" \
	]
	then
		for row in `seq 0 $MAX_TILE_Y`
		do
			#fixing size of last tile in each row
			local LAST_TILE_FILE="$TMP_DIR/`$FILE_GENERATOR $MAX_TILE_X $row`.jpg"
			local LAST_TILE_FIXED_FILE="$TMP_DIR/`$FILE_GENERATOR $MAX_TILE_X $row`.bmp"
			local OLD_WIDTH=`identify -format "%w" $LAST_TILE_FILE`
			local OLD_HEIGHT=`identify -format "%h" $LAST_TILE_FILE`
			if [ "$row" != "$MAX_TILE_Y" ]
			then
				#resizing last column of tiles to have TILE_SIZE height
				local NEW_WIDTH=`expr "$OLD_WIDTH * $TILE_SIZE / $OLD_HEIGHT" | bc`
				local NEW_HEIGHT=$TILE_SIZE
			else
				#resizing last tile to match the previous in the grid
				local NEW_HEIGHT=$LAST_TILE_HEIGHT
				local NEW_WIDTH=`echo "$OLD_WIDTH * $LAST_TILE_HEIGHT / $OLD_HEIGHT" | bc`
			fi
			convert "$LAST_TILE_FILE" -resize "${NEW_WIDTH}x${NEW_HEIGHT}!" "$LAST_TILE_FIXED_FILE"
			rm -f "$LAST_TILE_FILE"
		done

		montage \
			$TMP_DIR/* \
			-mode Concatenate \
			-geometry "${TILE_SIZE}x${TILE_SIZE}>" \
			-tile `expr $MAX_TILE_X + 1`x`expr $MAX_TILE_Y + 1` \
			$OUTPUT_FILE
		if [ ! "$NO_TRIM" ]
		then
			convert $OUTPUT_FILE -trim $OUTPUT_FILE
		fi
	fi
	
	rm -rf "$TMP_DIR"
}

# removes wrong symbols from filename, replacing them by underscores
makeOutputDir()
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
rsl()
{
	if [ $# -ne 1 ]
	then
		echo "Usage: $0 book_id"
		return 1
	fi

	local BOOK_ID=$1

	webGet "http://dlib.rsl.ru/loader/view/$1?get=pdf" "rsl.$BOOK_ID.pdf"
}

locMusdi()
{
	if [ $# -ne 1 ]
	then
		echo "Usage: $0 book_id"
		return 1
	fi

	local BOOK_ID=$1
	local MAX_PAGE=1000
	local OUTPUT_DIR="locMusdi.$BOOK_ID"

	#disabling global check
	MIN_FILE_SIZE_BYTES=0

	mkdir -p "$OUTPUT_DIR"
	for PAGE in `seq 1 $MAX_PAGE`
	do
		local BASENAME=`printf %04d $PAGE`
		true && \
			webGet "http://memory.loc.gov/musdi/$BOOK_ID/$BASENAME.tif" "$OUTPUT_DIR/$BASENAME.tif" || \
			webGet "http://memory.loc.gov/musdi/$BOOK_ID/$BASENAME.jpg" "$OUTPUT_DIR/$BASENAME.jpg" || \
			return 0
	done
}

hathi()
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
			webGet "https://babel.hathitrust.org/cgi/imgsrv/image?id=$BOOK_ID;seq=$PAGE;width=1000000" "$OUTPUT_DIR/`printf %04d.jpg $PAGE`"; \
			[ "$?" -ne 0 ] \
		)
		do
			sleep 30
		done;
	done;
}

gallica()
{
	if [ $# -le 3 ]
	then
		echo "Usage $0 ark_id [first_page] last_page"
		return 1
	fi

	local BOOK_ID=$1
	local OUTPUT_DIR=`makeOutputDir "gallica.$BOOK_ID"`
	shift;
	mkdir -p "$OUTPUT_DIR"
	for PAGE in `seq $@`
	do
		local PAGE_ID="${BOOK_ID}.f${PAGE}"
		local DOWNLOADED_FILE="${PAGE_ID}.bmp"
		local OUTPUT_FILE=`printf $OUTPUT_DIR/%04d.bmp $PAGE`
		if [ ! -f "$OUTPUT_FILE" ]
		then
			gallicaTiles "$PAGE_ID"
			mv "$DOWNLOADED_FILE" "$OUTPUT_FILE"
		fi
	done
}

britishLibrary()
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

vwml()
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
		local OUTPUT_FILE="$OUTPUT_DIR/\!`printf %04d $OUTPUT_PAGE`.jpg"
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
		if [ "$?" -eq "0" ]
		then
			local OUTPUT_PAGE=`expr $OUTPUT_PAGE + 1`
		fi
	done
}

#========================
#Tiled page downloaders
#========================
generalTilesFile()
{
	if [ $# -ne 2 ]
	then
		echo "Usage: $0 x y"
		return 1
	fi

	local TILE_X=$1
	local TILE_Y=$2

	printf "%04d_%04d" "$TILE_Y" "$TILE_X"
}

gallicaTilesUrl()
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

	echo "http://gallica.bnf.fr/iiif/ark:/12148/$BOOK_ID/$LEFT,$TOP,1024,1024/1024,/0/native.jpg"
}

gallicaTiles()
{
	if [ $# -ne 1 ]
	then
		echo "Usage: $0 ark_id"
		return 1
	fi

	#overriding global constant
	MIN_FILE_SIZE_BYTES=0

	local BOOK_ID=$1
	local ZOOM=6
	local TILE_SIZE=1024
	local OUTPUT_DIR=.

	tiles gallicaTilesUrl generalTilesFile dullValidate $BOOK_ID $ZOOM $TILE_SIZE $OUTPUT_DIR
}

haabTilesUrl()
{
	if [ $# -ne 4 ]
	then
		echo "Usage: $0 inage_id x y z"
		return 1
	fi

	local IMAGE_ID=`echo $1 | sed -e 's/\./\//g'`
	local TILE_X=$2
	local TILE_Y=$3
	local TILE_Z=$4
	local TILE_SIZE=1024

	local LEFT=`expr $TILE_X '*' $TILE_SIZE`
	local TOP=`expr $TILE_Y '*' $TILE_SIZE`

	echo "https://haab-digital.klassik-stiftung.de/viewer/iiif/image/$IMAGE_ID.tif/$LEFT,$TOP,1024,1024/1024,/0/default.jpg"
}

haabTiles()
{
	if [ $# -ne 1 ]
	then
		echo "Usage: $0 ark_id"
		return 1
	fi

	local BOOK_ID=$1
	local ZOOM=6
	local TILE_SIZE=1024
	local OUTPUT_DIR=.

	tiles haabTilesUrl generalTilesFile dullValidate $BOOK_ID $ZOOM $TILE_SIZE $OUTPUT_DIR
}

princetonTilesUrl()
{
	if [ $# -ne 4 ]
	then
		echo "Usage: $0 ark_id x y z"
		return 1
	fi

	local BOOK_ID=$1
	local TILE_X=$2
	local TILE_Y=$3
	local TILE_Z=$4
	local TILE_SIZE=1024

	local LEFT=`expr $TILE_X '*' $TILE_SIZE`
	local TOP=`expr $TILE_Y '*' $TILE_SIZE`

	echo "http://libimages.princeton.edu/loris/$BOOK_ID/$LEFT,$TOP,1024,1024/1024,/0/native.jpg"
}

princetonTiles()
{
	if [ $# -ne 1 ]
	then
		echo "Usage: $0 item_id"
		return 1
	fi

	#overriding global constant
	MIN_FILE_SIZE_BYTES=5120

	local BOOK_ID=$1
	local ZOOM=6
	local TILE_SIZE=1024
	local OUTPUT_DIR=.


	tiles princetonTilesUrl generalTilesFile dullValidate $BOOK_ID $ZOOM $TILE_SIZE $OUTPUT_DIR
}

dusseldorfTileFile()
{
	if [ $# -ne 2 ]
	then
		echo "Usage: $0 x y"
		return 1
	fi

	local TILE_X=$1
	local TILE_Y=$2
	local BASE_TILE_Y=50
	#dusseldorf tiles are numbered from bottom to top
	local REAL_TILE_Y=`expr $BASE_TILE_Y - $TILE_Y`

	generalTilesFile "$TILE_X" "$REAL_TILE_Y"
}

dusseldorfTilesUrl()
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
	local VERSION=1.0.0

	echo "http://digital.ub.uni-duesseldorf.de/image/tile/wc/nop/$UNKNOWN_NUMBER/$VERSION/$IMAGE_ID/$TILE_Z/$TILE_X/$TILE_Y.jpg"
}

dusseldorfTiles()
{
	if [ $# -ne 1 ]
	then
		echo "Usage: $0 image_id"
		return 1
	fi
	local BOOK_ID=$1
	local ZOOM=6
	local TILE_SIZE=512
	local OUTPUT_DIR=.

	#overriding global constant
	MIN_FILE_SIZE_BYTES=5120

	tiles dusseldorfTilesUrl dusseldorfTileFile dullValidate $BOOK_ID $ZOOM $TILE_SIZE $OUTPUT_DIR
}

uniHalleTileFile()
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

	generalTilesFile "$TILE_X" "$REAL_TILE_Y"
}

#quite similar to dusseldorf, with dirreferent magic numbers
uniHalleTilesUrl()
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
	local UNKNOWN_NUMBER=1157
	local VERSION=1.0.0

	echo "http://digitale.bibliothek.uni-halle.de/image/tile/wc/nop/$UNKNOWN_NUMBER/$VERSION/$IMAGE_ID/$TILE_Z/$TILE_X/$TILE_Y.jpg"
}

uniHalleTiles()
{
	if [ $# -ne 1 ]
	then
		echo "Usage: $0 image_id"
		return 1
	fi
	local BOOK_ID=$1
	local ZOOM=3
	local TILE_SIZE=512
	local OUTPUT_DIR=.

	#overriding global constant
	MIN_FILE_SIZE_BYTES=5120

	tiles uniHalleTilesUrl uniHalleTileFile dullValidate $BOOK_ID $ZOOM $TILE_SIZE $OUTPUT_DIR
}

uniJenaTilesUrl()
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

	echo "http://archive.thulb.uni-jena.de/tiles/hisbest/HisBest_derivate_00000416/$IMAGE_ID.tif/$TILE_Z/$TILE_Y/$TILE_X.jpg"
}

uniJenaTiles()
{
	if [ $# -ne 1 ]
	then
		echo "Usage: $0 image_id"
		return 1
	fi
	local BOOK_ID=$1
	local ZOOM=4
	local TILE_SIZE=256
	local OUTPUT_DIR=.

	#overriding global constant
	MIN_FILE_SIZE_BYTES=1

	tiles uniJenaTilesUrl generalTilesFile dullValidate $BOOK_ID $ZOOM $TILE_SIZE $OUTPUT_DIR
}

yaleWalpoleTilesUrl()
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

	for TILE_GROUP in `seq 0 2`
	do
		local URL="http://images.library.yale.edu/walpoleimages/dl/003000/$IMAGE_ID/TileGroup${TILE_GROUP}/$TILE_Z-$TILE_X-$TILE_Y.jpg"
		curl --silent -I "$URL" | grep "HTTP/1.1 200 OK" > /dev/null
		if [ "$?" -eq 0 ]
		then
			echo "$URL"
			return
		fi
	done

	echo "Failed to guess tile group for $URL"
	return 1
}

yaleWalpoleTiles()
{
	if [ $# -ne 1 ]
	then
		echo "Usage: $0 image_id"
		return 1
	fi
	local BOOK_ID=$1
	local ZOOM=5
	local TILE_SIZE=256
	local OUTPUT_DIR=.

	#overriding global constant
	MIN_FILE_SIZE_BYTES=256

	tiles yaleWalpoleTilesUrl generalTilesFile dullValidate $BOOK_ID $ZOOM $TILE_SIZE $OUTPUT_DIR
}

kunstkameraTilesUrl()
{
	if [ $# -ne 4 ]
	then
		echo "Usage: $0 image_id x y z"
		return 1
	fi

	local IMAGE_ID=$1
	local TILE_X=$2
	local TILE_Y=$3
	local TILE_SIZE=512

	local TILE_LEFT=`expr $TILE_X '*' $TILE_SIZE`
	local TILE_TOP=`expr $TILE_Y '*' $TILE_SIZE`

	echo "http://kunstkamera.ru/kunst-catalogue/spf/${IMAGE_ID}.jpg?w=${TILE_SIZE}&h=${TILE_SIZE}&cl=${TILE_LEFT}&ct=${TILE_TOP}&cw=${TILE_SIZE}&ch=${TILE_SIZE}"
}

kunstkameraTiles()
{
	if [ $# -ne 1 ]
	then
		echo "Usage: $0 image_id"
		return 1
	fi
	local BOOK_ID=$1
	local ZOOM=4
	local TILE_SIZE=512
	local OUTPUT_DIR=`makeOutputDir kunstkamera`

	#overriding global constant
	MIN_FILE_SIZE_BYTES=1

	tiles kunstkameraTilesUrl generalTilesFile dullValidate $BOOK_ID $ZOOM $TILE_SIZE $OUTPUT_DIR
}

ugentTilesUrl()
{
	if [ $# -ne 4 ]
	then
		echo "Usage $0 image_id x y z"
		return 1
	fi
	#expecting BOOK_ID in form of B3D7E912-00D1-11E6-BCF2-CC0ED53445F2:DS.42
	local BOOK_ID=$1
	local TILE_X=$2
	local TILE_Y=$3
	local ZOOM=$4
	local TILE_SIZE=1024
	
	local LEFT=`expr $TILE_X '*' $TILE_SIZE`
	local TOP=`expr $TILE_Y '*' $TILE_SIZE`

	#FIXME: this number should be manually adjusted to get correct results
	echo "http://adore.ugent.be/IIIF/images/archive.ugent.be:$BOOK_ID/$LEFT,$TOP,$TILE_SIZE,$TILE_SIZE/$TILE_SIZE,/0/default.jpg"
}

ugentTilesValidate()
{
	local TILE_FILE=$1
	local HEIGHT=`identify -format "%h" $TILE_FILE`
	#when out of bound, ugent will respond with some rainbow image with height=4000
	test $HEIGHT -ne 4000
	return $?
}

ugentTiles()
{
	if [ $# -ne 1 ]
	then
		echo "Usage: $0 image_id"
		return 1
	fi
	local BOOK_ID=$1
	local ZOOM=5
	local TILE_SIZE=1024
	local OUTPUT_DIR=`makeOutputDir ugent`

	#overriding global constant with some magic value (with 276 kilobytes)
	MIN_FILE_SIZE_BYTES=282624

	tiles ugentTilesUrl generalTilesFile ugentTilesValidate $BOOK_ID $ZOOM $TILE_SIZE $OUTPUT_DIR
}

uflEduTilesUrl()
{
	if [ $# -ne 4 ]
	then
		echo "Usage $0 image_id x y z"
		return 1
	fi
	#expecting BOOK_ID in form of
	#AA/00/03/94/08/00001/00522
	#(not including jp2 extension)
	local BOOK_ID=$1
	local TILE_X=$2
	local TILE_Y=$3
	local ZOOM=$4

	echo "http://ufdc.ufl.edu/iipimage/iipsrv.fcgi?DeepZoom=//flvc.fs.osg.ufl.edu/flvc-ufdc/resources/${BOOK_ID}.jp2_files/${ZOOM}/${TILE_X}_${TILE_Y}.jpg"
}

uflEduTiles()
{
	if [ $# -ne 1 ]
	then
		echo "Usage: $0 image_id"
		return 1
	fi
	local BOOK_ID="$1"
	local ZOOM=-1
	for TEST_ZOOM in `seq 13 -1 11`
	do
		if curl --fail --silent --head "`uflEduTilesUrl $BOOK_ID 0 0 $TEST_ZOOM`"
		then
			ZOOM=$TEST_ZOOM
			break
		fi
	done
	if [ $ZOOM -eq "-1" ]
	then
		echo "Unable to get max zoom"
		return 1
	fi
	local TILE_SIZE=256
	local OUTPUT_DIR=`makeOutputDir ufl.edu`

	local DZI_URL="http://ufdc.ufl.edu/iipimage/iipsrv.fcgi?DeepZoom=//flvc.fs.osg.ufl.edu/flvc-ufdc/resources/${BOOK_ID}.jp2.dzi"
	local IMG_WIDTH=`curl --silent "$DZI_URL" | sed 's/xmlns=".*"//g' | xmllint --xpath "string(/Image/Size/@Width)" -`
	local IMG_HEIGHT=`curl --silent "$DZI_URL" | sed 's/xmlns=".*"//g' | xmllint --xpath "string(/Image/Size/@Height)" -`

	#overriding global constants
	MIN_FILE_SIZE_BYTES=1
	MAX_TILE_X=`echo \`roundDiv ${IMG_WIDTH} 256\` - 1 | bc`
	MAX_TILE_Y=`echo \`roundDiv ${IMG_HEIGHT} 256\` - 1 | bc`

	tiles uflEduTilesUrl generalTilesFile dullValidate $BOOK_ID $ZOOM $TILE_SIZE $OUTPUT_DIR
}

uflEdu()
{
	if [ $# -ne 2 ]
	then
		echo "Usage $0 ark_id page_count"
		return 1
	fi

	#expecting BOOK_ID in form of
	#AA/00/03/94/08/00001
	local BOOK_ID=$1
	local OUTPUT_DIR=`makeOutputDir "gallica.$BOOK_ID"`
	local PAGE_COUNT=$2
	mkdir -p "$OUTPUT_DIR"
	for PAGE in `seq 1 $PAGE_COUNT`
	do
		local PAGE_ID="${BOOK_ID}/`printf %05d $PAGE`"
		local DOWNLOADED_FILE="${PAGE_ID}.bmp"
		local OUTPUT_FILE=`printf $OUTPUT_DIR/%04d.bmp $PAGE`
		if [ ! -f "$OUTPUT_FILE" ]
		then
			uflEduTiles "$PAGE_ID"
			mv "$DOWNLOADED_FILE" "$OUTPUT_FILE"
		fi
	done
}

habDeTilesUrl()
{
	if [ $# -ne 4 ]
	then
		echo "Usage $0 image_id x y z"
		return 1
	fi
	#expecting BOOK_ID in form of
	#AA/00/03/94/08/00001/00522
	#(not including jp2 extension)
	local BOOK_ID=$1
	local TILE_X=$2
	local TILE_Y=$3
	local ZOOM=$4
	
	for TILE_GROUP in `seq 0 2`
	do
		local URL="http://diglib.hab.de/varia/grafik/graph-a1-${BOOK_ID}/TileGroup${TILE_GROUP}/${ZOOM}-${TILE_X}-${TILE_Y}.jpg"
		curl --silent -I "$URL" | grep "HTTP/1.1 200 OK" > /dev/null
		if [ "$?" -eq 0 ]
		then
			echo "$URL"
			return
		fi
	done
}

habDeTiles()
{
	if [ $# -ne 1 ]
	then
		echo "Usage: $0 image_id"
		return 1
	fi
	local BOOK_ID="$1"
	local ZOOM=4
	local TILE_SIZE=256
	local OUTPUT_DIR=`makeOutputDir hab.de`

	#overriding global constants
	MIN_FILE_SIZE_BYTES=1

	tiles habDeTilesUrl generalTilesFile dullValidate $BOOK_ID $ZOOM $TILE_SIZE $OUTPUT_DIR
}

historyOrgTilesUrl()
{
	if [ $# -ne 4 ]
	then
		echo "Usage $0 image_id x y z"
		return 1
	fi
	local BOOK_ID=$1
	local TILE_X=$2
	local TILE_Y=$3
	local ZOOM=$4
	
	for TILE_GROUP in `seq 0 2`
	do
		local URL="http://www.history.org/history/museums/clothingexhibit/images/accessories/${BOOK_ID}/TileGroup${TILE_GROUP}/${ZOOM}-${TILE_X}-${TILE_Y}.jpg"
		curl --silent -I "$URL" | grep "HTTP/1.1 200 OK" > /dev/null
		if [ "$?" -eq 0 ]
		then
			echo "$URL"
			return
		fi
	done
}

historyOrgTiles()
{
	if [ $# -ne 1 ]
	then
		echo "Usage: $0 image_id"
		return 1
	fi
	local BOOK_ID="$1"
	local ZOOM=4
	local TILE_SIZE=256
	local OUTPUT_DIR=`makeOutputDir history.org`

	#overriding global constants
	MIN_FILE_SIZE_BYTES=1

	tiles historyOrgTilesUrl generalTilesFile dullValidate $BOOK_ID $ZOOM $TILE_SIZE $OUTPUT_DIR
}

npgTilesUrl()
{
	if [ $# -ne 4 ]
	then
		echo "Usage $0 image_id x y z"
		return 1
	fi
	local IMAGE_ID=$1
	local TILE_X=$2
	local TILE_Y=$3
	local ZOOM=$4
	
	echo "http://collectionimages.npg.org.uk/zoom/${IMAGE_ID}/zoomXML_files/${ZOOM}/${TILE_X}_${TILE_Y}.jpg"
}

npg()
{
	if [ $# -ne 1 ]
	then
		echo "Usage: $0 image_id"
		return 1
	fi
	local IMAGE_ID="$1"
	local ZOOM=11
	local TILE_SIZE=256
	local OUTPUT_DIR=`makeOutputDir npg`

	local DZI_URL="http://collectionimages.npg.org.uk/zoom/${IMAGE_ID}/zoomXML.dzi"
	local IMG_WIDTH=`curl --silent "$DZI_URL" | sed 's/xmlns=".*"//g' | xmllint --xpath "string(/Image/Size/@Width)" -`
	local IMG_HEIGHT=`curl --silent "$DZI_URL" | sed 's/xmlns=".*"//g' | xmllint --xpath "string(/Image/Size/@Height)" -`

	#overriding global constants
	MIN_FILE_SIZE_BYTES=1
	MAX_TILE_X=`echo "(${IMG_WIDTH} + 128) / 256 - 1" | bc`
	MAX_TILE_Y=`echo "(${IMG_HEIGHT} + 128) / 256 - 1" | bc`

	tiles npgTilesUrl generalTilesFile dullValidate $IMAGE_ID $ZOOM $TILE_SIZE $OUTPUT_DIR
}

if [ $# -lt 2 ]
then
	echo "Usage: $0 grabber <grabber params>"
	exit 1
fi

GRABBER=$1
shift
$GRABBER $@
