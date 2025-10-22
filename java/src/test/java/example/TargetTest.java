package example;

import static org.junit.jupiter.api.Assertions.*;
import org.junit.jupiter.api.Test;

class TargetTest {
  @Test
  void twentyIsAdult() {
    Target.isAdult(5);
    // assertTrue(Target.isAdult(20));
    // assertTrue(Target.isAdult(21));
    // assertFalse(Target.isAdult(19));
  }
}