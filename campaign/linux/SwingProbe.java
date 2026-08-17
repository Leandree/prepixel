// Tier-F probe app: standard Swing widgets + ONE custom-painted panel that mimics
// the OBS/qBittorrent shape (named container, painted content, no accessible children).
import javax.swing.*;
import javax.swing.border.TitledBorder;
import java.awt.*;

public class SwingProbe {
    static int clicks = 0;
    public static void main(String[] args) {
        SwingUtilities.invokeLater(() -> {
            JFrame f = new JFrame("SwingProbe");
            f.setDefaultCloseOperation(WindowConstants.EXIT_ON_CLOSE);
            f.setLayout(new BorderLayout(8, 8));

            JMenuBar mb = new JMenuBar();
            JMenu file = new JMenu("File");
            file.add(new JMenuItem("New"));
            file.add(new JMenuItem("Open"));
            file.add(new JMenuItem("Quit"));
            mb.add(file);
            mb.add(new JMenu("Help"));
            f.setJMenuBar(mb);

            JPanel top = new JPanel(new FlowLayout(FlowLayout.LEFT));
            JTextField input = new JTextField(24);
            input.getAccessibleContext().setAccessibleName("input-field");
            JButton btn = new JButton("Do it");
            JLabel status = new JLabel("clicks: 0");
            btn.addActionListener(e -> status.setText("clicks: " + (++clicks)));
            top.add(new JLabel("Type here:"));
            top.add(input);
            top.add(btn);
            top.add(status);
            f.add(top, BorderLayout.NORTH);

            JTextArea area = new JTextArea(8, 60);
            area.setText("The quick brown fox jumps over the lazy dog 0123456789");
            f.add(new JScrollPane(area), BorderLayout.CENTER);

            // the suspect: a named group whose content exists only as paint
            JPanel scope = new JPanel() {
                @Override protected void paintComponent(Graphics g0) {
                    super.paintComponent(g0);
                    Graphics2D g = (Graphics2D) g0;
                    g.setColor(new Color(18, 22, 30));
                    g.fillRect(0, 0, getWidth(), getHeight());
                    g.setColor(new Color(80, 200, 120));
                    int h = getHeight(), w = getWidth(), py = h / 2;
                    for (int x = 1; x < w; x++) {
                        int y = (int) (h / 2 + Math.sin(x / 14.0) * h / 3.2 * Math.sin(x / 97.0));
                        g.drawLine(x - 1, py, x, y);
                        py = y;
                    }
                    g.setColor(Color.WHITE);
                    g.setFont(g.getFont().deriveFont(16f));
                    g.drawString("PAINTED-ONLY-TEXT  42.7 dB  ch1/ch2", 14, 24);
                }
            };
            scope.setPreferredSize(new Dimension(860, 220));
            JPanel group = new JPanel(new BorderLayout());
            group.setBorder(new TitledBorder("Preview"));
            group.add(scope);
            f.add(group, BorderLayout.SOUTH);

            f.setSize(900, 640);
            f.setLocation(60, 40);
            f.setVisible(true);
        });
    }
}
