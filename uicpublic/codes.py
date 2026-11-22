"""Code tables from the RRC UIC database manual (UIA010), so the app can show words instead of codes."""

UIC_CLASS = {"2": "Injection/disposal", "5": "Storage, geothermal or brine"}

# UIC-TYPE-INJ, the codes in use since 06/01/95.
INJ_TYPE = {
    "1": "Disposal, nonproductive zone (W-14)",
    "2": "Disposal, productive zone (H-1)",
    "3": "Secondary or tertiary recovery",
    "4": "Miscellaneous",
    "5": "Liquid storage, salt formation (SWR 95)",
    "6": "Gas storage, reservoir (SWR 96)",
    "7": "Gas storage, salt formation (SWR 97)",
}

# Injection status reported on the latest H-10 (UIC-MONTR-W-STATUS) and on the H-5.
WELL_STATUS = {
    "1": "Authorized, not yet drilled",
    "2": "Drilled, not yet completed",
    "3": "Active",
    "4": "Temporarily abandoned",
    "5": "Other",
    # Not in the manual's list; the status comments in the data show what they mean.
    "6": "Permit cancelled",
    "7": "Plugged",
    "8": "Permit suspended",
}

# Enforcement action segment (UIENFACT).
ENF_VIOLATION = {
    "01": "W-2/G-1 requirement", "02": "Delinquent H-5", "03": "Delinquent H-10", "04": "Cement/confinement",
    "05": "Observation value", "06": "Tubing/packer", "07": "Packer depth", "08": "MIT failure",
    "09": "Injection pressure", "10": "Injection volume", "11": "Fluid type", "12": "Tubing-casing communication",
    "13": "Unauthorized commercial facility", "14": "Commercial facility requirements",
    "15": "Unauthorized zone change", "16": "No injection authority", "17": "14(b)(2) violation",
    "18": "Pollution", "19": "Citizen complaint", "20": "Operator complaint", "21": "Breakout",
}
ENF_NOTICE = {
    "01": "Shut-in", "02": "Sealed", "03": "Severed", "04": "Permit suspended", "05": "Permit cancelled",
    "06": "Penalty action", "07": "Plug hearing", "08": "Other",
}
ENF_COMPLIANCE = {
    "01": "According to rule", "02": "Plugged", "03": "Cancelled", "04": "Hearing", "05": "Cement squeeze",
    "06": "Repair/replace tubing", "07": "Repair/replace packer", "08": "Repair tubing and packer",
    "09": "Run liner", "10": "Other",
}

# H-10 violation segment (UI0HVIO), filings since the online H-10 system of 09/2007.
H10_VIOLATION = {
    "01": "Filing on plugged or cancelled permit",
    "02": "Packer depth more than 100 ft above permitted interval",
    "03": "Invalid lease ID",
    "05": "Fluid comment 'see comments'",
    "07": "Max pressure above permitted max + 100 psig",
    "08": "Liquid volume above permitted max + 1,000",
    "09": "Gas volume above permitted max + 1,000",
    "10": "Volume injected but no H-5 on file",
    "11": "Volume injected but no W-2/G-1 on file",
    "12": "Well not required to file H-10",
    "13": "Delinquent H-10",
    "14": "Same violation two years in a row",
    "15": "H-10 filed for dual completion wellbore",
    "16": "Annulus data missing for well with special condition",
    "18": "Salt water reported, not permitted",
    "19": "Brackish water reported, not permitted",
    "20": "Fresh water reported, not permitted",
    "21": "Air reported, not permitted",
    "22": "Gas reported, not permitted",
    "23": "CO2 reported, not permitted",
    "24": "Polymer reported, not permitted",
    "25": "NORM reported, not permitted",
    "26": "Top of injection zone deeper than permitted + 100 ft",
    "27": "Bottom of injection zone shallower than permitted - 100 ft",
    "30": "Positive volumes filed after well plugged",
}
H10_RESOLVED_BY = {"F": "Form", "H": "H-10", "O": "Other"}

H5_RESULT = {"P": "Passed", "F": "Failed", "I": "Inconclusive"}
H5_SCHEDULE_TYPE = {"I": "Initial", "A": "Annual", "F": "Five-year"}
H5_ALT_TEST = {"1": "Tracer survey", "2": "Temperature survey", "3": "Annulus fluid level", "4": "Other alternate"}


def label(table: dict, code) -> str:
    """'07 Max pressure ...' style text; the bare code when it is not in the table."""
    if code is None:
        return ""
    c = str(code).strip()
    return f"{c} {table[c]}" if c in table else c
