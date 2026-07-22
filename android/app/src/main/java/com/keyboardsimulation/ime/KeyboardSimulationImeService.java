package com.keyboardsimulation.ime;

import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.inputmethodservice.InputMethodService;
import android.os.Handler;
import android.os.Looper;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.view.inputmethod.InputConnection;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;

/**
 * Native Android IME for Keyboard Simulation.
 * Relays prepared text into the currently focused input field.
 */
public class KeyboardSimulationImeService extends InputMethodService {
    private static final String[] SCENES = new String[] {
        "默认", "表单/考试", "代码/IDE", "长文稳定"
    };

    private final Handler handler = new Handler(Looper.getMainLooper());
    private EditText relayText;
    private EditText delayInput;
    private EditText intervalInput;
    private CheckBox programMode;
    private CheckBox humanizeMode;
    private CheckBox slowStartMode;
    private TextView statusText;
    private TextView progressText;
    private Spinner sceneSpinner;

    private volatile boolean stopRequested = false;
    private volatile boolean pauseRequested = false;
    private volatile boolean running = false;

    private String resumeContent = "";
    private boolean resumeProgramMode = false;
    private long resumeIntervalMs = 15L;
    private boolean resumeHumanize = false;
    private boolean resumeSlowStart = true;
    private int resumeIndex = 0;
    private int resumeLineIndex = 0;
    private int resumeCharIndex = 0;
    private boolean resumeUseProgram = false;
    private String[] resumeLines = new String[0];
    private int totalUnits = 0;
    private int doneUnits = 0;

    @Override
    public View onCreateInputView() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(10), dp(8), dp(10), dp(8));
        root.setBackgroundResource(R.drawable.panel_background);

        LinearLayout sceneRow = new LinearLayout(this);
        sceneRow.setOrientation(LinearLayout.HORIZONTAL);
        sceneRow.setGravity(Gravity.CENTER_VERTICAL);
        sceneSpinner = new Spinner(this);
        ArrayAdapter<String> adapter = new ArrayAdapter<>(
            this, android.R.layout.simple_spinner_dropdown_item, SCENES
        );
        sceneSpinner.setAdapter(adapter);
        sceneSpinner.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                applyScene(SCENES[position]);
            }
            @Override public void onNothingSelected(AdapterView<?> parent) {}
        });
        sceneRow.addView(label("场景"));
        sceneRow.addView(sceneSpinner);
        root.addView(sceneRow);

        LinearLayout options = new LinearLayout(this);
        options.setOrientation(LinearLayout.HORIZONTAL);
        options.setGravity(Gravity.CENTER_VERTICAL);
        delayInput = smallNumberInput("3");
        intervalInput = smallNumberInput("15");
        programMode = new CheckBox(this);
        programMode.setText("程序模式");
        humanizeMode = new CheckBox(this);
        humanizeMode.setText("抖动");
        slowStartMode = new CheckBox(this);
        slowStartMode.setText("慢启动");
        slowStartMode.setChecked(true);

        options.addView(label("延迟(s)"));
        options.addView(delayInput);
        options.addView(label("间隔(ms)"));
        options.addView(intervalInput);
        options.addView(programMode);
        options.addView(humanizeMode);
        options.addView(slowStartMode);
        root.addView(options);

        relayText = new EditText(this);
        relayText.setMinLines(4);
        relayText.setMaxLines(8);
        relayText.setGravity(Gravity.TOP | Gravity.START);
        relayText.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        relayText.setHint("输入需要中转输出的内容");

        ScrollView scroll = new ScrollView(this);
        scroll.addView(relayText, new ScrollView.LayoutParams(
            ScrollView.LayoutParams.MATCH_PARENT,
            ScrollView.LayoutParams.WRAP_CONTENT
        ));
        root.addView(scroll, new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            0,
            1
        ));

        LinearLayout tools = new LinearLayout(this);
        tools.setOrientation(LinearLayout.HORIZONTAL);
        Button pasteClip = new Button(this);
        pasteClip.setText("粘贴剪贴板");
        pasteClip.setOnClickListener(v -> pasteFromClipboard());
        Button cleanBtn = new Button(this);
        cleanBtn.setText("清洗");
        cleanBtn.setOnClickListener(v -> cleanRelayText());
        Button clearBtn = new Button(this);
        clearBtn.setText("清空");
        clearBtn.setOnClickListener(v -> relayText.setText(""));
        tools.addView(pasteClip);
        tools.addView(cleanBtn);
        tools.addView(clearBtn);
        root.addView(tools);

        LinearLayout actions = new LinearLayout(this);
        actions.setOrientation(LinearLayout.HORIZONTAL);
        Button startButton = new Button(this);
        startButton.setText("开始输出");
        startButton.setOnClickListener(v -> startRelay(false));
        Button pauseButton = new Button(this);
        pauseButton.setText("暂停/继续");
        pauseButton.setOnClickListener(v -> togglePause());
        Button continueButton = new Button(this);
        continueButton.setText("断点续打");
        continueButton.setOnClickListener(v -> startRelay(true));
        Button stopButton = new Button(this);
        stopButton.setText("停止");
        stopButton.setOnClickListener(v -> {
            stopRequested = true;
            pauseRequested = false;
            setStatus("正在停止...");
        });
        actions.addView(startButton);
        actions.addView(pauseButton);
        actions.addView(continueButton);
        actions.addView(stopButton);
        root.addView(actions);

        progressText = new TextView(this);
        progressText.setText("进度 0/0");
        root.addView(progressText);

        statusText = new TextView(this);
        statusText.setText("切换到目标输入框后开始。本地运行，不上传内容。");
        root.addView(statusText);

        return root;
    }

    private void applyScene(String scene) {
        if ("表单/考试".equals(scene)) {
            delayInput.setText("3");
            intervalInput.setText("25");
            programMode.setChecked(false);
            humanizeMode.setChecked(true);
            slowStartMode.setChecked(true);
        } else if ("代码/IDE".equals(scene)) {
            delayInput.setText("3");
            intervalInput.setText("8");
            programMode.setChecked(true);
            humanizeMode.setChecked(false);
            slowStartMode.setChecked(true);
        } else if ("长文稳定".equals(scene)) {
            delayInput.setText("3");
            intervalInput.setText("12");
            programMode.setChecked(false);
            humanizeMode.setChecked(false);
            slowStartMode.setChecked(true);
        } else {
            delayInput.setText("3");
            intervalInput.setText("15");
            programMode.setChecked(false);
            humanizeMode.setChecked(false);
            slowStartMode.setChecked(true);
        }
        setStatus("已应用场景：" + scene);
    }

    private void pasteFromClipboard() {
        ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
        if (cm == null || !cm.hasPrimaryClip()) {
            setStatus("剪贴板为空。");
            return;
        }
        ClipData data = cm.getPrimaryClip();
        if (data == null || data.getItemCount() == 0) {
            setStatus("剪贴板为空。");
            return;
        }
        CharSequence text = data.getItemAt(0).coerceToText(this);
        if (text == null) {
            setStatus("剪贴板为空。");
            return;
        }
        relayText.setText(text.toString());
        setStatus("已从剪贴板载入。");
    }

    private void cleanRelayText() {
        String text = relayText.getText().toString();
        text = text.replace("\uFEFF", "")
            .replace("\u200B", "")
            .replace("\u200C", "")
            .replace("\u200D", "")
            .replace("\u2060", "");
        text = text.replace("\r\n", "\n").replace('\r', '\n');
        String[] lines = text.split("\n", -1);
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < lines.length; i++) {
            if (i > 0) sb.append('\n');
            sb.append(rtrim(lines[i]));
        }
        relayText.setText(sb.toString());
        setStatus("已清洗文本。");
    }

    private static String rtrim(String value) {
        int end = value.length();
        while (end > 0) {
            char ch = value.charAt(end - 1);
            if (ch != ' ' && ch != '\t') break;
            end--;
        }
        return value.substring(0, end);
    }

    private void togglePause() {
        if (!running) {
            setStatus("当前没有运行中的任务。");
            return;
        }
        pauseRequested = !pauseRequested;
        setStatus(pauseRequested ? "已暂停。" : "已继续。");
    }

    private void startRelay(boolean fromCheckpoint) {
        if (running) {
            setStatus("任务进行中，请先停止或暂停。");
            return;
        }

        final String content;
        final boolean codeMode;
        final long delayMs;
        final long intervalMs;
        final boolean humanize;
        final boolean slowStart;

        if (fromCheckpoint) {
            if (resumeContent == null || resumeContent.isEmpty() || totalUnits <= 0 || doneUnits >= totalUnits) {
                setStatus("当前没有可续打的断点。");
                return;
            }
            content = resumeContent;
            codeMode = resumeProgramMode;
            delayMs = 0L;
            intervalMs = resumeIntervalMs;
            humanize = resumeHumanize;
            slowStart = resumeSlowStart;
        } else {
            content = relayText.getText().toString();
            if (content.isEmpty()) {
                setStatus("没有内容。");
                return;
            }
            codeMode = programMode.isChecked();
            delayMs = Math.max(0, parseLong(delayInput, 3)) * 1000L;
            intervalMs = Math.max(0, parseLong(intervalInput, 15));
            humanize = humanizeMode.isChecked();
            slowStart = slowStartMode.isChecked();

            resumeContent = content;
            resumeProgramMode = codeMode;
            resumeIntervalMs = intervalMs;
            resumeHumanize = humanize;
            resumeSlowStart = slowStart;
            resumeIndex = 0;
            resumeLineIndex = 0;
            resumeCharIndex = 0;
            resumeUseProgram = codeMode;
            doneUnits = 0;

            String normalized = content.replace("\r\n", "\n").replace('\r', '\n');
            if (codeMode) {
                resumeLines = normalized.split("\n", -1);
                totalUnits = 0;
                for (String line : resumeLines) {
                    totalUnits += line.length();
                }
                totalUnits += Math.max(0, resumeLines.length - 1); // newlines + clear ops counted loosely
            } else {
                resumeLines = new String[0];
                totalUnits = normalized.length();
            }
        }

        stopRequested = false;
        pauseRequested = false;
        running = true;
        setStatus((delayMs / 1000.0) + " 秒后开始。");
        setProgress();

        handler.postDelayed(() -> {
            InputConnection input = getCurrentInputConnection();
            if (input == null) {
                running = false;
                setStatus("当前没有可输入的目标。");
                return;
            }
            if (resumeUseProgram) {
                emitProgramLines(input, resumeLines, resumeLineIndex, resumeCharIndex, intervalMs, humanize, slowStart, doneUnits);
            } else {
                String normalized = resumeContent.replace("\r\n", "\n").replace('\r', '\n');
                emitText(input, normalized, resumeIndex, intervalMs, humanize, slowStart, doneUnits);
            }
        }, delayMs);
    }

    private long computeInterval(long baseIntervalMs, int unitIndex, boolean humanize, boolean slowStart) {
        double value = baseIntervalMs;
        if (slowStart) {
            if (unitIndex < 8) {
                value *= (2.2 - unitIndex * 0.12);
            } else if (unitIndex < 16) {
                value *= 1.3;
            }
        }
        if (humanize && value > 0) {
            double factor = 0.8 + Math.random() * 0.4;
            value *= factor;
        }
        return Math.max(0L, Math.round(value));
    }

    private void emitText(
        InputConnection input,
        String text,
        int index,
        long intervalMs,
        boolean humanize,
        boolean slowStart,
        int unitsDone
    ) {
        if (stopRequested) {
            resumeIndex = index;
            doneUnits = unitsDone;
            running = false;
            setStatus("已停止，断点 " + unitsDone + "/" + totalUnits + "。可断点续打。");
            setProgress();
            return;
        }
        if (pauseRequested) {
            resumeIndex = index;
            doneUnits = unitsDone;
            handler.postDelayed(() -> emitText(input, text, index, intervalMs, humanize, slowStart, unitsDone), 80);
            return;
        }
        if (index >= text.length()) {
            running = false;
            doneUnits = totalUnits;
            setStatus("输出完成。");
            setProgress();
            return;
        }

        input.commitText(String.valueOf(text.charAt(index)), 1);
        int nextDone = unitsDone + 1;
        resumeIndex = index + 1;
        doneUnits = nextDone;
        setProgress();
        long wait = computeInterval(intervalMs, index, humanize, slowStart);
        handler.postDelayed(
            () -> emitText(input, text, index + 1, intervalMs, humanize, slowStart, nextDone),
            wait
        );
    }

    private void emitProgramLines(
        InputConnection input,
        String[] lines,
        int lineIndex,
        int charIndex,
        long intervalMs,
        boolean humanize,
        boolean slowStart,
        int unitsDone
    ) {
        if (stopRequested) {
            resumeLineIndex = lineIndex;
            resumeCharIndex = charIndex;
            doneUnits = unitsDone;
            running = false;
            setStatus("已停止，断点行 " + (lineIndex + 1) + "。可断点续打。");
            setProgress();
            return;
        }
        if (pauseRequested) {
            resumeLineIndex = lineIndex;
            resumeCharIndex = charIndex;
            doneUnits = unitsDone;
            handler.postDelayed(
                () -> emitProgramLines(input, lines, lineIndex, charIndex, intervalMs, humanize, slowStart, unitsDone),
                80
            );
            return;
        }
        if (lineIndex >= lines.length) {
            running = false;
            doneUnits = totalUnits;
            setStatus("输出完成。");
            setProgress();
            return;
        }

        if (charIndex == 0 && lineIndex > 0) {
            input.commitText("\n", 1);
            clearAutoIndent(input);
            unitsDone += 1;
            doneUnits = unitsDone;
            setProgress();
        }

        String line = lines[lineIndex];
        if (charIndex >= line.length()) {
            resumeLineIndex = lineIndex + 1;
            resumeCharIndex = 0;
            long wait = computeInterval(intervalMs, unitsDone, humanize, slowStart);
            int finalUnits = unitsDone;
            handler.postDelayed(
                () -> emitProgramLines(input, lines, lineIndex + 1, 0, intervalMs, humanize, slowStart, finalUnits),
                wait
            );
            return;
        }

        input.commitText(String.valueOf(line.charAt(charIndex)), 1);
        int nextDone = unitsDone + 1;
        resumeLineIndex = lineIndex;
        resumeCharIndex = charIndex + 1;
        doneUnits = nextDone;
        setProgress();
        long wait = computeInterval(intervalMs, nextDone, humanize, slowStart);
        handler.postDelayed(
            () -> emitProgramLines(input, lines, lineIndex, charIndex + 1, intervalMs, humanize, slowStart, nextDone),
            wait
        );
    }

    private void clearAutoIndent(InputConnection input) {
        CharSequence beforeCursor = input.getTextBeforeCursor(256, 0);
        if (beforeCursor == null) {
            return;
        }
        String text = beforeCursor.toString();
        int lineStart = text.lastIndexOf('\n') + 1;
        String currentLine = text.substring(lineStart);
        int removable = 0;
        while (removable < currentLine.length()) {
            char ch = currentLine.charAt(removable);
            if (ch != ' ' && ch != '\t') {
                return;
            }
            removable++;
        }
        if (removable > 0) {
            input.deleteSurroundingText(removable, 0);
        }
    }

    private void setProgress() {
        if (progressText != null) {
            progressText.setText("进度 " + doneUnits + "/" + Math.max(totalUnits, doneUnits));
        }
    }

    private EditText smallNumberInput(String defaultValue) {
        EditText input = new EditText(this);
        input.setText(defaultValue);
        input.setInputType(InputType.TYPE_CLASS_NUMBER);
        input.setSingleLine(true);
        input.setSelectAllOnFocus(true);
        input.setEms(3);
        return input;
    }

    private TextView label(String text) {
        TextView view = new TextView(this);
        view.setText(text);
        view.setPadding(dp(6), 0, dp(4), 0);
        return view;
    }

    private long parseLong(EditText input, long fallback) {
        try {
            return Long.parseLong(input.getText().toString().trim());
        } catch (NumberFormatException exc) {
            return fallback;
        }
    }

    private void setStatus(String text) {
        if (statusText != null) {
            statusText.setText(text);
        }
    }

    private int dp(int value) {
        float density = getResources().getDisplayMetrics().density;
        return Math.round(value * density);
    }
}