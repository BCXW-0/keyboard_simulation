package com.keyboardimmulation.ime;

import android.inputmethodservice.InputMethodService;
import android.os.Handler;
import android.os.Looper;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.view.inputmethod.InputConnection;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

public class KeyboardImmulationImeService extends InputMethodService {
    private final Handler handler = new Handler(Looper.getMainLooper());
    private EditText relayText;
    private EditText delayInput;
    private EditText intervalInput;
    private CheckBox programMode;
    private TextView statusText;
    private boolean stopRequested = false;

    @Override
    public View onCreateInputView() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(10), dp(8), dp(10), dp(8));
        root.setBackgroundResource(com.keyboardimmulation.ime.R.drawable.panel_background);

        LinearLayout options = new LinearLayout(this);
        options.setOrientation(LinearLayout.HORIZONTAL);
        options.setGravity(Gravity.CENTER_VERTICAL);

        delayInput = smallNumberInput("3");
        intervalInput = smallNumberInput("15");
        programMode = new CheckBox(this);
        programMode.setText("程序输入模式");

        options.addView(label("延迟(s)"));
        options.addView(delayInput);
        options.addView(label("间隔(ms)"));
        options.addView(intervalInput);
        options.addView(programMode);
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

        LinearLayout actions = new LinearLayout(this);
        actions.setOrientation(LinearLayout.HORIZONTAL);
        Button startButton = new Button(this);
        startButton.setText("开始输出");
        startButton.setOnClickListener(v -> startRelay());
        Button stopButton = new Button(this);
        stopButton.setText("停止");
        stopButton.setOnClickListener(v -> {
            stopRequested = true;
            setStatus("正在停止...");
        });
        actions.addView(startButton);
        actions.addView(stopButton);
        root.addView(actions);

        statusText = new TextView(this);
        statusText.setText("切到目标输入框后开始。");
        root.addView(statusText);

        return root;
    }

    private void startRelay() {
        String content = relayText.getText().toString();
        if (content.isEmpty()) {
            setStatus("没有内容。");
            return;
        }

        stopRequested = false;
        long delayMs = Math.max(0, parseLong(delayInput, 3)) * 1000L;
        long intervalMs = Math.max(0, parseLong(intervalInput, 15));
        boolean codeMode = programMode.isChecked();

        setStatus((delayMs / 1000.0) + " 秒后开始。");
        handler.postDelayed(() -> emitContent(content, codeMode, intervalMs), delayMs);
    }

    private void emitContent(String content, boolean codeMode, long intervalMs) {
        InputConnection input = getCurrentInputConnection();
        if (input == null) {
            setStatus("当前没有可输入的目标。");
            return;
        }

        String normalized = content.replace("\r\n", "\n").replace('\r', '\n');
        if (!codeMode) {
            emitText(input, normalized, 0, intervalMs);
            return;
        }

        String[] lines = normalized.split("\n", -1);
        emitProgramLines(input, lines, 0, intervalMs);
    }

    private void emitText(InputConnection input, String text, int index, long intervalMs) {
        if (stopRequested) {
            setStatus("已停止。");
            return;
        }
        if (index >= text.length()) {
            setStatus("输出完成。");
            return;
        }

        input.commitText(String.valueOf(text.charAt(index)), 1);
        handler.postDelayed(() -> emitText(input, text, index + 1, intervalMs), intervalMs);
    }

    private void emitProgramLines(InputConnection input, String[] lines, int lineIndex, long intervalMs) {
        if (stopRequested) {
            setStatus("已停止。");
            return;
        }
        if (lineIndex >= lines.length) {
            setStatus("输出完成。");
            return;
        }

        if (lineIndex > 0) {
            input.commitText("\n", 1);
            clearAutoIndent(input);
        }

        emitLineThenNext(input, lines, lineIndex, 0, intervalMs);
    }

    private void emitLineThenNext(InputConnection input, String[] lines, int lineIndex, int charIndex, long intervalMs) {
        if (stopRequested) {
            setStatus("已停止。");
            return;
        }

        String line = lines[lineIndex];
        if (charIndex >= line.length()) {
            setStatus("输出中: " + (lineIndex + 1) + "/" + lines.length + " 行");
            handler.postDelayed(() -> emitProgramLines(input, lines, lineIndex + 1, intervalMs), intervalMs);
            return;
        }

        input.commitText(String.valueOf(line.charAt(charIndex)), 1);
        handler.postDelayed(() -> emitLineThenNext(input, lines, lineIndex, charIndex + 1, intervalMs), intervalMs);
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

    private EditText smallNumberInput(String defaultValue) {
        EditText input = new EditText(this);
        input.setText(defaultValue);
        input.setInputType(InputType.TYPE_CLASS_NUMBER);
        input.setSingleLine(true);
        input.setSelectAllOnFocus(true);
        input.setEms(4);
        return input;
    }

    private TextView label(String text) {
        TextView view = new TextView(this);
        view.setText(text);
        view.setPadding(dp(8), 0, dp(4), 0);
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
