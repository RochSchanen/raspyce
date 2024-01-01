#!/usr/bin/python3

# absolutely no speed optimisation
# the coding style is for development

_DEBUG = [
    "NONE",
    #"ALL",
    #"TRANSFER",
    #"TRACE",
    #"DELAY",
]

_DELAY = 1

# debug flags checker
def _debug(*flags):
    if "NONE" in _DEBUG: return False
    if "ALL"  in _DEBUG: return True
    # search for one valid flag
    for f in flags:
        if f in _DEBUG:
            # at least one match
            return True
    # no valid flags were found -> False
    if flags:
        return False
    # empty parameter -> always True
    # except if 'NONE' is set explicitly -> always False
    return True

# the spi class
class spi():

    """
        In a terminal use the "pinout"
        command to display the pin layout
        of your raspberry pi. The pin
        numbers below are the pin indices
        that runs from 1 to 40. The buit-in
        spi library is not used. However,
        the pin numbers below are matching
        the buit-in spi connections for
        convenience.
    """

    PIN_CS   = 24   # GPIO08 for Chip Select (buit-in value CS0)
    PIN_SCK  = 23   # GPIO11 for Clock (buit-in value SCK)
    PIN_MISO = 21   # GPIO09 for Master In Slave Out (buit-in value MISO)
    PIN_MOSI = 19   # GPIO10 for Master Out Slave In (buit-in value MOSI)

    """
        The clock polarity and data phase depends
        on the slave device mode/configuration.
        check from the device data sheet. Most
        commonly used is CPOL = 0 and CPHA = 0.

        Also, the data bit width determines how many bit
        are send during one data transfer. for one byte at
        a time, use the bit width value of 8.
    """

    CPOL = 0    # data loading on rising clock
    CPHA = 0    # data updating on falling clock
    BITW = 8    # data bit width

    def __init__(self):

        from RPi.GPIO import setmode, BOARD, BCM
        # use the pin number designation mode
        # (the alternate designation mode is BCM)
        setmode(BOARD)

        from RPi.GPIO import setwarnings
        # avoid warnings when multiple script run concurently
        setwarnings(False)

        from RPi.GPIO import setup, IN, OUT
        from RPi.GPIO import output, HIGH, LOW
        
        # deactivate chip select (CS0 = 1)
        setup(self.PIN_CS, OUT)
        output(self.PIN_CS, HIGH)

        # setup other spi pin directions
        # (MASTER is the raspberry pi):
        # MOSI > out
        # MISO < in
        # SCK  > out
        setup([self.PIN_SCK, self.PIN_MOSI], OUT)
        setup(self.PIN_MISO, IN)

        return

    def printinfo(self):
        """ display local system info """
        from RPi.GPIO import RPI_INFO
        for r in RPI_INFO.keys():
            print(f"{r} = {RPI_INFO[r]}")
        return

    def wait(self, duration):
        """ wait for a given duration (in milliseconds) """
        from time import sleep
        sleep(duration/1000)
        return

    def transfer(self, data):

        """
            Sequences are strings of 0 and 1 that
            defines the pin levels during the data
            transfer. The character '1' for level
            high and character '0' for level low.
            A bit is transfered every clock cycle.
            Each cycle is subdivised in two halves.
            Thus, an n bits transfer requires 2n
            halves. An extra half cycle is present
            to allow for the chip select signal to
            fall and rise at the start and at the
            end of the sequence. data it the value
            to transfer and is given as an integer
            number.
            """

        w = self.BITW
        # build select sequence
        SEL_SQ =  f"1{w*'00'}01" # chip select
        # build clock sequences
        CLK_S0 =  f"0{w*'01'}00" # clock levels (CPOL 0)
        CLK_S1 =  f"1{w*'10'}11" # clock levels (CPOL 1)
        # formatting string for data output sequence
        FS = f"0{w}b"
        # build data output sequences
        DTO = "".join([f"{c}{c}" for c in f"{data:{FS}}"])
        DTO_S0 =  f"0{DTO}00" # data levels (CPHA 0)
        DTO_S1 =  f"00{DTO}0" # data levels (CPHA 1)
        # build data read trigger sequence
        # (This defines when to record the MISO pin value)
        TRG = f"{w*'01'}"
        TRG_S0 =  f"0{TRG}00" # record triggers (CPHA 0)
        TRG_S1 =  f"00{TRG}0" # record triggers (CPHA 1)
        # select mode (from the values of CPOL and CPHAS)
        CLK_SQ = [CLK_S0, CLK_S1][self.CPOL]
        DTO_SQ = [DTO_S0, DTO_S1][self.CPHA]
        TRG_SQ = [TRG_S0, TRG_S1][self.CPHA]
        # buid casting dictionaries: characters to GPIO levels
        from RPi.GPIO import output as pinwrite
        from RPi.GPIO import input as pinread
        from RPi.GPIO import HIGH, LOW
        # type casting dicos
        LEVEL = {"0": LOW, "1": HIGH}
        SYMBL = {LOW: "0", HIGH: "1"}
        # declare input lists
        DATA, MISO = [], []
        # transfer
        for SEL, CLK, DTO, TRG in zip(SEL_SQ, CLK_SQ, DTO_SQ, TRG_SQ):
            # process I/O (outputs before inputs)
            pinwrite(self.PIN_MOSI, LEVEL[DTO])
            pinwrite(self.PIN_SCK, LEVEL[CLK])
            pinwrite(self.PIN_CS, LEVEL[SEL])
            MISO.append(SYMBL[pinread(self.PIN_MISO)])
            # record input value on trigger
            if TRG == "1": DATA.append(MISO[-1])
            # debug
            if _debug("DELAY"): s.wait(_DELAY)
        # debug
        if _debug("TRANSFER"):
            print(f"---------- transfer ----------\n")
            print(f"{'DATA VALUE ':>15}b{data:08b} = x{data:02x} = d{data}")
        if _debug("TRACE"):
            self.display_sequence(SEL_SQ, f"{'SELECT ':>15}")
            self.display_sequence(CLK_SQ, f"{'CLOCK ':>15}")
            self.display_sequence(DTO_SQ, f"{'MOSI ':>15}")
            self.display_sequence(''.join(MISO), f"{'INPUT LEVEL':>15}")
            self.display_sequence(TRG_SQ, f"{'READ TRIGGER ':>15}")
            print()
        if _debug("TRANSFER"):
            print(f"{'DATA VALUE ':>15}b{int(''.join(DATA), 2):08b}")
            print()
        return int("".join(DATA), 2)

    # display sequence using a set of unicode chars
    def display_sequence(self, SQ, NAME):
        """ the following set of unicode chars are used
            u2504 ┄ u2510 ┐ u2534 ┴ u2500 ─
            u2514 └ u2518 ┘ u252C ┬ u250C ┌
        """
        # init sequence at unknown state
        l, T, B = "U", "┄", "┄"
        # level transition dictionaries (think machine state)
        level_to_level = {
            "U": {"0": ("┐ ", "┴─"), "1": ("┬─", "┘ "), "U": ("┄┄", "┄┄")},
            "0": {"0": ("  ", "──"), "1": ("┌─", "┘ "), },
            "1": {"0": ("┐ ", "└─"), "1": ("──", "  "), },
            }
        # run through sequence
        for c in SQ:
            # get unicode pattern (top and bottom chars)
            t, b = level_to_level[l][c]
            # update state (level value) and strings (top and bottom)
            l, T, B = c, T+t, B+b
        # display
        print(f"{' ':{len(NAME)}}{''.join(T)}")
        print(f"{NAME}{''.join(B)}")
        # done
        return

if __name__ == "__main__":
    # try using a loop back setup for testing: connect MISO to MOSI

    _DELAY = 1
    
    _DEBUG = [
        #"NONE",
        #"ALL",
        "TRANSFER",
        "TRACE",
        #"DELAY",
        "CLEANUP",
    ]
    
    s = spi()
    s.transfer(0b00001111)
    s.transfer(0b11110000)
    
    if _debug("CLEANUP"): 
        s.wait(500)
        from RPi.GPIO import cleanup
        cleanup()
