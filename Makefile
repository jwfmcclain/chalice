.DEFAULT_GOAL := all
.PHONY: clean statemachines

TARGET_DIR=/Volumes/CIRCUITPY
LIB_DIR=$(TARGET_DIR)/lib

CODE=$(addprefix $(TARGET_DIR)/, code.py astral.py gps.py)
LIBS=$(addprefix $(LIB_DIR)/, adafruit_gps.mpy)

$(TARGET_DIR)/%.py: %.py
	cp $< $@

$(TARGET_DIR)/lib/%: lib/%
	rsync -a $< $(TARGET_DIR)/lib

$(LIB_DIR): 
	mkdir $@

$(LIBS): | $(LIB_DIR)

clean:
	rm -f $(CODE)
	rm -rf $(LIB_DIR)

statemachines:
	$(MAKE) -C statemachines install

all: $(CODE) $(LIBS) statemachines
