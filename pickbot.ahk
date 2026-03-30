#Requires AutoHotkey v2.0
#SingleInstance Force

SetTitleMatchMode 2
SetControlDelay -1

global AppState := Map(
    "Running", false,
    "Busy", false,
    "ConfigPath", A_ScriptDir "\config.ini",
    "LogPath", A_ScriptDir "\logs\pickbot.log",
    "TargetWinTitle", "",
    "LoopIntervalMs", 3000,
    "Steps", [],
    "LastCycleTick", 0
)

EnsureLogDir()
LoadConfig()
SetTimer(LoopTick, 250)

F8::ToggleRun()
F9::ReloadBotConfig()
F10::ExitApp()

LoopTick() {
    global AppState

    if !AppState["Running"] || AppState["Busy"] {
        return
    }

    now := A_TickCount
    if AppState["LastCycleTick"] != 0 && now - AppState["LastCycleTick"] < AppState["LoopIntervalMs"] {
        return
    }

    hwnd := WinExist(AppState["TargetWinTitle"])
    if !hwnd {
        Log("Target window not found: " AppState["TargetWinTitle"])
        return
    }

    AppState["Busy"] := true
    try {
        for _, step in AppState["Steps"] {
            ExecuteStep(hwnd, step)
        }
        AppState["LastCycleTick"] := A_TickCount
        Log("Cycle completed.")
    } catch Error as err {
        Log("Cycle failed: " err.Message)
    } finally {
        AppState["Busy"] := false
    }
}

ExecuteStep(hwnd, step) {
    stepType := step["Type"]

    switch stepType {
        case "Key":
            ControlSend(step["Value"], , "ahk_id " hwnd)
            Log("Sent key sequence: " step["Value"])
        case "Text":
            ControlSendText(step["Value"], , "ahk_id " hwnd)
            Log("Sent text: " step["Value"])
        case "Click":
            pos := "x" step["X"] " y" step["Y"]
            ControlClick(pos, "ahk_id " hwnd, , step["Button"], step["Count"], "NA Pos")
            Log("Clicked at " step["X"] "," step["Y"] " with " step["Button"])
        case "Sleep":
            Sleep(step["DurationMs"])
            Log("Slept for " step["DurationMs"] " ms")
        default:
            throw Error("Unsupported step type: " stepType)
    }

    delayMs := step.Has("DelayMs") ? step["DelayMs"] : 0
    if delayMs > 0 {
        Sleep(delayMs)
    }
}

ToggleRun() {
    global AppState
    AppState["Running"] := !AppState["Running"]
    AppState["LastCycleTick"] := 0

    if AppState["Running"] {
        Log("Bot started.")
        TrayTip("Loop started", "pickbot", 1)
    } else {
        Log("Bot stopped.")
        TrayTip("Loop stopped", "pickbot", 1)
    }
}

ReloadBotConfig() {
    LoadConfig()
    Log("Config reloaded.")
    TrayTip("Config reloaded", "pickbot", 1)
}

LoadConfig() {
    global AppState

    configPath := AppState["ConfigPath"]
    if !FileExist(configPath) {
        throw Error("Missing config file: " configPath)
    }

    targetWinTitle := IniRead(configPath, "Target", "WinTitle", "")
    if targetWinTitle = "" {
        throw Error("Target.WinTitle is required.")
    }

    loopIntervalMs := ToInt(IniRead(configPath, "Loop", "IntervalMs", "3000"), "Loop.IntervalMs")
    steps := LoadSteps(configPath)
    if steps.Length = 0 {
        throw Error("At least one [StepN] section is required.")
    }

    AppState["TargetWinTitle"] := targetWinTitle
    AppState["LoopIntervalMs"] := loopIntervalMs
    AppState["Steps"] := steps
    AppState["LastCycleTick"] := 0

    Log("Config loaded for target: " targetWinTitle)
}

LoadSteps(configPath) {
    steps := []
    index := 1

    loop {
        section := "Step" index
        stepType := IniRead(configPath, section, "Type", "")
        if stepType = "" {
            break
        }

        step := Map("Type", stepType)

        switch stepType {
            case "Key", "Text":
                step["Value"] := IniRead(configPath, section, "Value", "")
                step["DelayMs"] := ToInt(IniRead(configPath, section, "DelayMs", "0"), section ".DelayMs")
                if step["Value"] = "" {
                    throw Error(section ".Value is required for " stepType)
                }
            case "Click":
                step["X"] := ToInt(IniRead(configPath, section, "X", "0"), section ".X")
                step["Y"] := ToInt(IniRead(configPath, section, "Y", "0"), section ".Y")
                step["Button"] := IniRead(configPath, section, "Button", "Left")
                step["Count"] := ToInt(IniRead(configPath, section, "Count", "1"), section ".Count")
                step["DelayMs"] := ToInt(IniRead(configPath, section, "DelayMs", "0"), section ".DelayMs")
            case "Sleep":
                step["DurationMs"] := ToInt(IniRead(configPath, section, "DurationMs", "0"), section ".DurationMs")
                if step["DurationMs"] < 0 {
                    throw Error(section ".DurationMs must be >= 0")
                }
            default:
                throw Error("Unsupported step type in " section ": " stepType)
        }

        steps.Push(step)
        index += 1
    }

    return steps
}

EnsureLogDir() {
    global AppState
    logDir := A_ScriptDir "\logs"
    if !DirExist(logDir) {
        DirCreate(logDir)
    }
}

Log(message) {
    global AppState
    timestamp := FormatTime(, "yyyy-MM-dd HH:mm:ss")
    FileAppend(timestamp " | " message "`n", AppState["LogPath"], "UTF-8")
}

ToInt(value, fieldName) {
    if !RegExMatch(value, "^-?\d+$") {
        throw Error(fieldName " must be an integer, got: " value)
    }
    return value + 0
}
