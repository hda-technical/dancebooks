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
	set tempFile = tempFolder.CreateTextFile(outFile, True)
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
	set tempFile = tempFolder.CreateTextFile(outFile, True)
	tempFile.Write _
		"Windows Registry Editor Version 5.00"&vbCrLf&_
		"[-HKEY_CLASSES_ROOT\bib]"&vbCrLf
	tempFile.Close
	fname = tempFolder + "\"+outFile
	res = shell.Run(fname,1,true)
	if Err.Number <> 0 then
		msgbox "Uninstall failed. Check permissions.",vbSystemModal,"Bibiography URL Handler"
	end if
	fs.DeleteFile outFile
end sub

sub open(arg)
	on error resume next
	set tempFile = fs.GetFile(WScript.ScriptFullName)
	strFolder = fs.GetParentFolderName(tempFile) 

	arg = mid(arg,5)
	arg = replace(arg,"//","/")
	arg = replace(arg,"\\","\")
	arg = replace(arg,"/","\")

	path = strFolder + urlDecode(arg)
	res = shell.Run("""" + path + """")
	if Err.Number <> 0 then
		msgbox "No such file. Try re-syncing the library.",vbSystemModal,"Bibiography URL Handler"
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

function urlDecode(s)
	dim jsEngine
	set jsEngine = CreateObject("MSScriptControl.ScriptControl")
	jsEngine.Language = "JScript"
	urlDecode = Replace(s, "+", " ")
    urlDecode = jsEngine.CodeObject.decodeURIComponent(urlDecode)
end function