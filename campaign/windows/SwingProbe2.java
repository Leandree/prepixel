import javax.swing.*;

/** Round 2: NO setAccessibleName overrides — default accessible names only,
 *  to measure whether JAB exposes the labels' real painted text. */
public class SwingProbe2 {
    public static void main(String[] args) {
        SwingUtilities.invokeLater(() -> {
            JFrame f = new JFrame("pipeline-tap Swing probe 2");
            f.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
            JPanel p = new JPanel();
            p.setLayout(new BoxLayout(p, BoxLayout.Y_AXIS));
            p.add(new JLabel("SWING-TAP-SENTINEL café naïve 日本語 END"));
            p.add(new JTextField("initial", 20));
            JLabel counter = new JLabel("count=0");
            JButton bump = new JButton("Increment");
            final int[] n = {0};
            bump.addActionListener(e -> counter.setText("count=" + (++n[0])));
            p.add(bump);
            p.add(counter);
            f.getContentPane().add(p);
            f.setSize(480, 260);
            f.setLocation(240, 180);
            f.setVisible(true);
        });
    }
}
