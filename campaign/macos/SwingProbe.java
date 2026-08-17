import javax.swing.*;
import java.awt.*;

/** Throwaway Swing probe for the Java tier (pipeline-tap campaign). */
public class SwingProbe {
    public static void main(String[] args) {
        SwingUtilities.invokeLater(() -> {
            JFrame f = new JFrame("pipeline-tap Swing probe");
            f.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
            JPanel p = new JPanel();
            p.setLayout(new BoxLayout(p, BoxLayout.Y_AXIS));
            JLabel sentinel = new JLabel("SWING-TAP-SENTINEL café naïve 日本語 END");
            sentinel.getAccessibleContext().setAccessibleName("sentinel-label");
            JTextField field = new JTextField("initial", 20);
            field.getAccessibleContext().setAccessibleName("probe-field");
            JLabel counter = new JLabel("count=0");
            counter.getAccessibleContext().setAccessibleName("counter-label");
            JButton bump = new JButton("Increment");
            final int[] n = {0};
            bump.addActionListener(e -> counter.setText("count=" + (++n[0])));
            p.add(sentinel); p.add(field); p.add(bump); p.add(counter);
            f.getContentPane().add(p);
            f.setSize(480, 260);
            f.setLocation(240, 180);
            f.setVisible(true);
        });
    }
}
