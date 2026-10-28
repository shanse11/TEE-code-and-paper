on run argv
	set inPath to item 1 of argv
	set outPath to item 2 of argv
	set inFile to POSIX file inPath as alias
	set outFile to POSIX file outPath
	tell application "Pages"
		with timeout of 3600 seconds
			set theDoc to open inFile
			set frontmost to true
			export theDoc to outFile as PDF
			delay 2
			close theDoc saving no
		end timeout
	end tell
	return "OK"
end run
