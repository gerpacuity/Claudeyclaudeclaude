.PHONY: install preview generate upload clean help web

help:
	@echo "DogVid — Automated Dog Video Generator"
	@echo ""
	@echo "Commands:"
	@echo "  make install       Install dependencies"
	@echo "  make preview       Generate a 30-second preview"
	@echo "  make generate      Generate a full 10-hour video (calming_sleep preset)"
	@echo "  make upload        Upload the latest video to YouTube"
	@echo "  make list          List available presets and scenes"
	@echo "  make web           Start the web UI (http://localhost:5000)"
	@echo "  make clean         Remove generated output files"
	@echo ""
	@echo "Custom generation:"
	@echo "  dogvid generate --name 'My Video' --mood relaxed --duration 10h"
	@echo "  dogvid generate --preset calming_sleep"
	@echo "  dogvid preview --scene bouncing_shapes --duration 30s"

install:
	pip install -e .
	@echo ""
	@echo "Checking for ffmpeg..."
	@which ffmpeg > /dev/null 2>&1 || echo "WARNING: ffmpeg not found. Install it: sudo apt install ffmpeg"
	@echo "Done! Run 'dogvid --help' to get started."

preview:
	dogvid preview --duration 30s --resolution 720p

generate:
	dogvid generate --preset calming_sleep --duration 10h

upload:
	@echo "Upload the generated video:"
	@echo "  dogvid upload output/calming_sleep.mp4 --title '10 Hours Dog TV' --privacy private"

list:
	dogvid list-scenes
	@echo ""
	dogvid list-audio
	@echo ""
	dogvid list-presets

web:
	python -m dogvid.web.run

clean:
	rm -rf output/
	@echo "Output directory cleaned."
