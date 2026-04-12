import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'features/chat/chat_screen.dart';
import 'shared/theme.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // TODO: Firebase 초기화 (firebase_options.dart 생성 후 활성화)
  // await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);

  runApp(
    const ProviderScope(
      child: LouisApp(),
    ),
  );
}

class LouisApp extends StatelessWidget {
  const LouisApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '루이스',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      themeMode: ThemeMode.system,
      home: const ChatScreen(),
    );
  }
}
