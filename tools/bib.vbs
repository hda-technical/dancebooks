on error resume next
set fs=CreateObject("Scripting.FileSystemObject")
set shell = CreateObject("WScript.Shell")

if WScript.Arguments.Count = 0 then
	install
elseif WScript.Arguments.Item(0) = "uninstall" then
	uninstall
else
	open WScript.Arguments.Item(0)
end if

sub install
	on error resume next
	outFile=fs.GetTempName + ".reg"
	set tempFolder = fs.GetSpecialFolder(2) 
	set tempFile = tempFolder.CreateTextFile(outFile, true)
	tempFile.Write _
		"Windows Registry Editor Version 5.00" & vbCrLf & _
		"[HKEY_CLASSES_ROOT\bib]" & vbCrLf & _
		"@=""URL:Bibliography Protocol""" & vbCrLf & _
		"""URL Protocol""=""""" & vbCrLf & _
		"[HKEY_CLASSES_ROOT\bib\DefaultIcon]" & vbCrLf & _
		"@=""\""bib.cmd\""""" & vbCrLf & _
		"[HKEY_CLASSES_ROOT\bib\shell]" & vbCrLf & _
		"[HKEY_CLASSES_ROOT\bib\shell\open]" & vbCrLf & _
		"[HKEY_CLASSES_ROOT\bib\shell\open\command]" & vbCrLf & _
		"@=""\""wscript.exe\"" \""" & _
		replace(WScript.ScriptFullName, "\", "\\") & _
		"\"" \""%1\""""" & vbCrLf
	tempFile.Close
	filename = tempFolder + "\" + outFile
	res = shell.Run(filename, 1, true)
	if Err.Number <> 0 then
		msgbox "Install failed. Check permissions.", vbSystemModal, "Bibiography URL Handler"
	end if
	tempFolder.DeleteFile outFile
end sub

sub uninstall
	on error resume next
	outFile=fs.GetTempName + ".reg"
	'msgbox outfile
	set tempFolder = fs.GetSpecialFolder(2) 
	set tempFile = tempFolder.CreateTextFile(outFile, true)
	tempFile.Write _
		"Windows Registry Editor Version 5.00" & vbCrLf & _
		"[-HKEY_CLASSES_ROOT\bib]" & vbCrLf
	tempFile.Close
	fname = tempFolder + "\" + outFile
	res = shell.Run(fname, 1, true)
	if Err.Number <> 0 then
		msgbox "Uninstall failed. Check permissions.", vbSystemModal, "Bibiography URL Handler"
	end if
	fs.DeleteFile outFile
end sub

sub open(arg)
	on error resume next
	set tempFile = fs.GetFile(WScript.ScriptFullName)
	strFolder = fs.GetParentFolderName(fs.GetParentFolderName(tempFile))

	arg = mid(arg,5)
	arg = replace(arg,"//","/")
	arg = replace(arg,"\\","\")
	arg = replace(arg,"/","\")

	path = strFolder + "\" + urlDecode(arg)
	res = shell.Run("""" + path + """")
	if Err.Number <> 0 then
		msgbox "No such file. Try re-syncing the library.", vbSystemModal, "Bibiography URL Handler"
	end if
end sub

function readFromRegistry(strRegistryKey, strDefault)
    dim value

    on error resume next
    set shell = CreateObject("WScript.Shell")
    value = shell.RegRead(strRegistryKey)

    if err.number <> 0 then
        readFromRegistry = strDefault
    else
        readFromRegistry = value
    end if
end function

function urlDecode(str)
	str = EncodeUTF8(str) 'Fucking Firefox doesn't encode its address strings into UTF8
    set list = CreateObject("System.Collections.ArrayList")
    strLen = len(str)
    for i = 1 to strLen
        sT = mid(str, i, 1)
        if sT = "%" then
            if i + 2 <= strLen then
                list.add cbyte("&H" & mid(str, i + 1, 2))
                i = i + 2
            end if
        else
            list.add asc(sT)
        end if
    next
    depth = 0
    for each by in list.toArray()
        if by and &h80 then
            if (by and &h40) = 0 then
                if depth = 0 then Err.Raise 5
                val = val * 2 ^ 6 + (by and &h3f)
                depth = depth - 1
                if depth = 0 then
                    sR = sR & chrw(val)
                    val = 0
                end if
            elseif (by and &h20) = 0 then
                if depth > 0 then Err.Raise 5
                val = by and &h1f
                depth = 1
            elseif (by and &h10) = 0 then
                if depth > 0 then Err.Raise 5
                val = by and &h0f
                depth = 2
            else
                Err.Raise 5
            end if
        else
            if depth > 0 then Err.Raise 5
            sR = sR & chrw(by)
        end if
    next
    if depth > 0 then Err.Raise 5
    urlDecode = sR

end function

Function EncodeUTF8(s)
    Dim i, c, utfc, b1, b2, b3
    
    For i=1 to Len(s)
        c = ToLong(AscW(Mid(s,i,1)))
 
        If c < 128 Then
            utfc = chr( c)
        ElseIf c < 2048 Then
            b1 = c Mod &h40
            b2 = (c - b1) / &h40
            utfc = chr(&hC0 + b2) & chr(&h80 + b1)
        ElseIf c < 65536 And (c < 55296 Or c > 57343) Then
            b1 = c Mod &h40
            b2 = ((c - b1) / &h40) Mod &h40
            b3 = (c - b1 - (&h40 * b2)) / &h1000
            utfc = chr(&hE0 + b3) & chr(&h80 + b2) & chr(&h80 + b1)
        Else
            ' Младший или старший суррогат UTF-16
            utfc = Chr(&hEF) & Chr(&hBF) & Chr(&hBD)
        End If

        EncodeUTF8 = EncodeUTF8 + utfc
    Next
End Function

Function ToLong(intVal)
    If intVal < 0 Then
        ToLong = CLng(intVal) + &H10000
    Else
        ToLong = CLng(intVal)
    End If
End Function