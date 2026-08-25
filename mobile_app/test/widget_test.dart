import 'package:flutter_test/flutter_test.dart';
import 'package:servease/main.dart';

void main() {
  testWidgets('ServEase App smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const ServEaseApp());
    expect(find.text('ServEase'), findsOneWidget);
  });
}
