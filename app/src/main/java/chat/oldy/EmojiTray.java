package chat.oldy;
import android.view.*;import android.widget.*;import org.json.*;

final class EmojiTray {
 static final String[] NAMES={"Смайлы","Жесты","Любовь","Игры","Еда","Стикеры"};
 static final String[] ICONS={"☺","👍","♡","🎮","☕","▣"};
 static final String[] FACES={
  "😀 😃 😄 😁 😆 😅 😂 🤣 🥹 😊 😇 🙂 🙃 😉 😌 😍 🥰 😘 😋 😜 🤪 😎 🥳 🤩 🫠 🫡 🫢 🫣 🫥 🫤 🥲 🥺 😭 😤 🤬 🤯 😳 😨 😱 🤔 🧐 🤓 😴 🥱 🤐 🤒 🤕 🤧",
  "👍 👎 👏 🙌 🫶 🤝 🙏 💪 🦾 👊 ✊ 🤛 🤜 ✌️ 🤞 🫰 🤟 🤘 👌 🤌 🤏 👈 👉 👆 👇 ☝️ 🖐️ ✋ 🫳 🫴 👋 🫱 🫲 👀 👂 🧠",
  "❤️ 🧡 💛 💚 💙 💜 🖤 🤍 🤎 🩷 🩵 🩶 💔 ❤️‍🔥 ❤️‍🩹 💕 💞 💓 💗 💖 💘 💝 💟 🫶 🥰 😍 😘 🌹 💐 ✨ 🥹",
  "🎮 🕹️ 👾 🤖 🎲 ♟️ 🧩 🏆 🥇 🎯 🏁 ⚽ 🏀 🎾 🏎️ 🚀 🛸 ⚡ 🔥 💯 💥 💫 🪄 💎 🛡️ ⚔️ 🏹 🧙 🧛 🧟 🐉 👻 💀 😈 👑 🌌 🌃",
  "☕ 🍵 🧋 🥤 🧃 🥛 🍿 🍫 🍪 🍩 🎂 🍰 🧁 🍦 🍕 🍔 🍟 🌭 🥪 🌮 🌯 🍜 🍝 🍣 🍱 🥟 🥗 🥑 🍎 🍌 🍓 🍒 🫐 🍇 🍉 🍊"
 };
 static void show(MainActivity a){if(a.emojiPanel==null||a.compose==null)return;if(a.emojiPanel.getVisibility()==View.VISIBLE){a.emojiPanel.setVisibility(View.GONE);return;}((android.view.inputmethod.InputMethodManager)a.getSystemService(android.content.Context.INPUT_METHOD_SERVICE)).hideSoftInputFromWindow(a.compose.getWindowToken(),0);a.emojiPanel.setVisibility(View.VISIBLE);fill(a,0);}
 static void fill(MainActivity a,int category){if(a.emojiPanel==null)return;a.emojiPanel.removeAllViews();a.emojiPanel.setBackground(a.shape(a.CARD,18));
  LinearLayout shortcuts=a.row();shortcuts.addView(a.button(I18n.t("☺ Смайлы"),category<5,()->fill(a,0)),new LinearLayout.LayoutParams(0,a.dp(48),1));shortcuts.addView(a.button(I18n.t("▣ Стикеры"),category==5,()->fill(a,5)),new LinearLayout.LayoutParams(0,a.dp(48),1));a.emojiPanel.addView(shortcuts);
  LinearLayout head=a.row();TextView label=a.label(I18n.t(NAMES[category]),15,a.MUTED);label.setPadding(a.dp(12),0,0,0);head.addView(label,new LinearLayout.LayoutParams(0,a.dp(38),1));head.addView(a.button("×",false,()->a.emojiPanel.setVisibility(View.GONE)),new LinearLayout.LayoutParams(a.dp(38),a.dp(38)));a.emojiPanel.addView(head);
  if(category==5){LinearLayout actions=a.col();actions.addView(a.button(I18n.t("Создать из фото"),true,()->PersonalStickers.create(a,true)));a.space(actions,6);actions.addView(a.button(I18n.t("Создать по описанию"),false,()->PersonalStickers.create(a,false)));a.space(actions,6);actions.addView(a.button(I18n.t("Открыть мои стикеры"),false,()->PersonalStickers.show(a)));a.pad(actions,10);a.emojiPanel.addView(actions);return;}
  LinearLayout tabs=a.row();for(int i=0;i<5;i++){final int n=i;TextView tab=a.label(ICONS[i],22,category==i?a.GREEN:a.MUTED);tab.setGravity(Gravity.CENTER);tab.setContentDescription(I18n.t(NAMES[i]));if(i==category)tab.setBackground(a.shape(a.light?0xffd6e9fc:0xff2e3555,12));tab.setOnClickListener(v->{fill(a,n);} );tabs.addView(tab,new LinearLayout.LayoutParams(0,a.dp(38),1));}a.emojiPanel.addView(tabs);
  ScrollView scroll=new ScrollView(a);scroll.setVerticalScrollBarEnabled(true);GridLayout grid=new GridLayout(a);int columns=Math.max(4,(a.getResources().getDisplayMetrics().widthPixels-a.dp(40))/a.dp(48));grid.setColumnCount(columns);scroll.addView(grid);
  String[] values=FACES[category].split(" ");int cellHeight=52;
  for(int i=0;i<values.length;i++){final int n=i;TextView cell=a.label(values[i],29,a.TEXT);cell.setGravity(Gravity.CENTER);
   GridLayout.LayoutParams lp=new GridLayout.LayoutParams(GridLayout.spec(i/columns),GridLayout.spec(i%columns,1f));lp.width=0;lp.height=a.dp(cellHeight);grid.addView(cell,lp);
   cell.setOnClickListener(v->{int at=Math.max(0,a.compose.getSelectionStart());a.compose.getText().insert(at,values[n]);a.selectedMotion=-1;});
  }
  a.emojiPanel.addView(scroll,new LinearLayout.LayoutParams(-1,Math.min(a.dp(cellHeight*4),(int)(a.getResources().getDisplayMetrics().heightPixels*.27f))));a.space(a.emojiPanel,4);
 }
}
