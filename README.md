

Build: pyinstaller Vista.py --onedir





- [X] add to artdaemon
	- [X] create SegmanRepo/Service_Vista and put exe inside
	- [X] edit CreateMyServices.ps1
		Add this to bottom:
			$Path = "ServiceVista"
			./CreateService.ps1 -ServiceName Vista -CommandName Vista.cmd -PackageName $Package -PathName $Path
	- [X] edit Services_install.bat
	- [X] create cmd files manually in SegmanRepo/ServiceVista (not sure how they are auto created)
		- [X] install.cmd
			@echo off
			call Service_Vista_install
		- [X] status.cmd
			@echo off
			call Service_Vista_status
		- [X] uninstall.cmd
			@echo off
			call Service_Vista_uninstall
		- [X] create Vista.cmd
			Vista.exe --config config.json
	- [X] run ConfigMyServices.cmd
	- [X] edit linkexes.cmd
	- [X] change to building with --onedir
		- [X] symlink from SegmanRepo/ServiceVista/Vista.exe to distribute/ArtDaemon/bin/Vista.exe
		- [X] symlink from distribute/ArtDaemon/bin/Vista.exe to distribute/Vista3D/Vista.exe (actual exe)
		- [X] _internal folder at distribute/Vista3D/_internal/
		- [X] models folder in SegmanRepo/ServiceVista/models
		- [X] config.json in SegmanRepo/ServiceVista/config.json