import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../../services/api_service.dart';
import '../worker/worker_shell.dart';
import '../provider/provider_shell.dart';
import '../admin/admin_shell.dart';

class OtpVerificationScreen extends StatefulWidget {
  final String email;
  final String role;
  final String fullName;

  const OtpVerificationScreen({
    super.key,
    required this.email,
    required this.role,
    required this.fullName,
  });

  @override
  State<OtpVerificationScreen> createState() => _OtpVerificationScreenState();
}

class _OtpVerificationScreenState extends State<OtpVerificationScreen> {
  final List<TextEditingController> _digitControllers = List.generate(6, (_) => TextEditingController());
  final List<FocusNode> _focusNodes = List.generate(6, (_) => FocusNode());

  bool _isVerifying = false;
  bool _isResending = false;
  String? _errorMessage;

  // 60-second resend cooldown timer
  Timer? _timer;
  int _secondsRemaining = 60;

  @override
  void initState() {
    super.initState();
    _startCooldownTimer();
    // Auto-focus first digit after frame renders
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _focusNodes[0].requestFocus();
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    for (final c in _digitControllers) {
      c.dispose();
    }
    for (final f in _focusNodes) {
      f.dispose();
    }
    super.dispose();
  }

  void _startCooldownTimer() {
    setState(() {
      _secondsRemaining = 60;
    });
    _timer?.cancel();
    _timer = Timer.periodic(const Duration(seconds: 1), (t) {
      if (!mounted) return;
      if (_secondsRemaining > 0) {
        setState(() => _secondsRemaining--);
      } else {
        t.cancel();
      }
    });
  }

  String get _currentOtp => _digitControllers.map((c) => c.text.trim()).join();

  void _onDigitChanged(int index, String value) {
    setState(() => _errorMessage = null);

    // Handle multi-character paste (e.g. user pasted full 6 digits)
    if (value.length > 1) {
      final clean = value.replaceAll(RegExp(r'\D'), '');
      if (clean.length == 6) {
        for (int i = 0; i < 6; i++) {
          _digitControllers[i].text = clean[i];
        }
        _focusNodes[5].requestFocus();
        _handleVerify();
        return;
      }
    }

    if (value.isNotEmpty) {
      if (index < 5) {
        _focusNodes[index + 1].requestFocus();
      } else {
        _focusNodes[index].unfocus();
        if (_currentOtp.length == 6) {
          _handleVerify();
        }
      }
    }
  }

  void _handleVerify() async {
    final otp = _currentOtp;
    if (otp.length != 6) {
      setState(() => _errorMessage = 'Please enter the complete 6-digit code.');
      return;
    }

    setState(() {
      _isVerifying = true;
      _errorMessage = null;
    });

    final res = await ApiService.verifyOtp(email: widget.email, otp: otp);

    if (!mounted) return;

    if (res['success'] == true) {
      setState(() {
        _isVerifying = false;
      });

      // Show polished success dialog before proceeding
      _showSuccessModalAndNavigate(res['role'] ?? widget.role);
    } else {
      setState(() {
        _isVerifying = false;
        _errorMessage = res['message'] ?? 'Incorrect verification code. Please try again.';
      });
      // Clear inputs on error and focus first box
      for (final c in _digitControllers) {
        c.clear();
      }
      _focusNodes[0].requestFocus();
    }
  }

  void _handleResend() async {
    if (_secondsRemaining > 0 || _isResending) return;

    setState(() {
      _isResending = true;
      _errorMessage = null;
    });

    final res = await ApiService.resendOtp(email: widget.email);

    if (!mounted) return;

    setState(() => _isResending = false);

    if (res['success'] == true) {
      _startCooldownTimer();
      for (final c in _digitControllers) {
        c.clear();
      }
      _focusNodes[0].requestFocus();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(res['message'] ?? 'A new verification code was sent to your email.'),
          backgroundColor: AppColors.forest900,
        ),
      );
    } else {
      setState(() => _errorMessage = res['message'] ?? 'Failed to resend code.');
    }
  }

  void _showSuccessModalAndNavigate(String role) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        contentPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 28),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppColors.forest900,
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: AppColors.forest900.withValues(alpha: 0.2),
                    blurRadius: 16,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: const Icon(Icons.check_rounded, color: AppColors.goldAccent, size: 40),
            ),
            const SizedBox(height: 18),
            const Text(
              'Email Verified!',
              style: TextStyle(
                fontFamily: 'Sora',
                fontSize: 22,
                fontWeight: FontWeight.bold,
                color: AppColors.ink900,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Welcome to ServEase, ${widget.fullName}!\nYour account is now fully active.',
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 13, color: AppColors.slate600, height: 1.4),
            ),
            const SizedBox(height: 24),
            AppButton(
              label: 'Go to Workspace',
              icon: Icons.arrow_forward_rounded,
              isFullWidth: true,
              onPressed: () {
                Navigator.pop(ctx);
                _routeToRoleShell(role);
              },
            ),
          ],
        ),
      ),
    );
  }

  void _routeToRoleShell(String role) {
    Widget destination;
    if (role == 'worker') {
      destination = const WorkerShell();
    } else if (role == 'provider') {
      destination = const ProviderShell();
    } else if (role == 'admin') {
      destination = const AdminShell();
    } else {
      destination = const WorkerShell();
    }

    Navigator.pushAndRemoveUntil(
      context,
      MaterialPageRoute(builder: (_) => destination),
      (route) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.cream50,
      appBar: AppBar(
        title: const Text('Email Verification'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_rounded),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            physics: const BouncingScrollPhysics(),
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
            child: AppResponsiveContainer(
              maxWidth: 460,
              padding: EdgeInsets.zero,
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  // Header Illustration Badge
                  Container(
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(
                      color: AppColors.forest900,
                      borderRadius: BorderRadius.circular(24),
                      boxShadow: [
                        BoxShadow(
                          color: AppColors.forest900.withValues(alpha: 0.15),
                          blurRadius: 16,
                          offset: const Offset(0, 6),
                        ),
                      ],
                    ),
                    child: const Icon(
                      Icons.mark_email_read_rounded,
                      color: AppColors.goldAccent,
                      size: 40,
                    ),
                  ),
                  const SizedBox(height: 20),

                  const Text(
                    'Check Your Email',
                    style: TextStyle(
                      fontFamily: 'Sora',
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                      color: AppColors.ink900,
                      letterSpacing: -0.5,
                    ),
                  ),
                  const SizedBox(height: 8),

                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: RichText(
                      textAlign: TextAlign.center,
                      text: TextSpan(
                        style: const TextStyle(fontSize: 14, color: AppColors.slate600, height: 1.4),
                        children: [
                          const TextSpan(text: 'We sent a 6-digit verification code to:\n'),
                          TextSpan(
                            text: widget.email,
                            style: const TextStyle(
                              fontWeight: FontWeight.bold,
                              color: AppColors.forest900,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 24),

                  // Verification Card
                  AppCard(
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        // Error message if any
                        if (_errorMessage != null) ...[
                          Container(
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: AppColors.error.withValues(alpha: 0.1),
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(color: AppColors.error.withValues(alpha: 0.3)),
                            ),
                            child: Row(
                              children: [
                                const Icon(Icons.error_outline_rounded, color: AppColors.error, size: 18),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    _errorMessage!,
                                    style: const TextStyle(fontSize: 12, color: AppColors.error, fontWeight: FontWeight.w600),
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(height: 16),
                        ],

                        // 6-Digit PIN Boxes
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: List.generate(6, (index) {
                            return SizedBox(
                              width: 44,
                              height: 54,
                              child: KeyboardListener(
                                focusNode: FocusNode(),
                                onKeyEvent: (KeyEvent event) {
                                  if (event is KeyDownEvent &&
                                      event.logicalKey == LogicalKeyboardKey.backspace &&
                                      _digitControllers[index].text.isEmpty &&
                                      index > 0) {
                                    _focusNodes[index - 1].requestFocus();
                                  }
                                },
                                child: TextField(
                                  controller: _digitControllers[index],
                                  focusNode: _focusNodes[index],
                                  textAlign: TextAlign.center,
                                  keyboardType: TextInputType.number,
                                  inputFormatters: [
                                    FilteringTextInputFormatter.digitsOnly,
                                    LengthLimitingTextInputFormatter(6),
                                  ],
                                  style: const TextStyle(
                                    fontSize: 22,
                                    fontWeight: FontWeight.bold,
                                    fontFamily: 'monospace',
                                    color: AppColors.ink900,
                                  ),
                                  decoration: InputDecoration(
                                    contentPadding: EdgeInsets.zero,
                                    fillColor: _focusNodes[index].hasFocus ? AppColors.white : AppColors.cream50,
                                    filled: true,
                                    border: OutlineInputBorder(
                                      borderRadius: BorderRadius.circular(12),
                                      borderSide: const BorderSide(color: AppColors.border, width: 1.5),
                                    ),
                                    focusedBorder: OutlineInputBorder(
                                      borderRadius: BorderRadius.circular(12),
                                      borderSide: const BorderSide(color: AppColors.forest900, width: 2),
                                    ),
                                  ),
                                  onChanged: (val) => _onDigitChanged(index, val),
                                ),
                              ),
                            );
                          }),
                        ),
                        const SizedBox(height: 16),

                        // Expiry Badge
                        const Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.timer_outlined, size: 14, color: AppColors.slate600),
                            SizedBox(width: 4),
                            Text(
                              'Code expires in 5 minutes',
                              style: TextStyle(fontSize: 12, color: AppColors.slate600),
                            ),
                          ],
                        ),
                        const SizedBox(height: 24),

                        // Verify Action Button
                        AppButton(
                          label: 'Verify & Complete Registration',
                          icon: Icons.verified_user_rounded,
                          isLoading: _isVerifying,
                          isFullWidth: true,
                          onPressed: _isVerifying ? null : _handleVerify,
                        ),
                        const SizedBox(height: 16),

                        // Resend Section
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Text(
                              "Didn't receive the code? ",
                              style: TextStyle(fontSize: 13, color: AppColors.slate600),
                            ),
                            if (_secondsRemaining > 0)
                              Text(
                                'Resend in ${_secondsRemaining}s',
                                style: const TextStyle(
                                  fontSize: 13,
                                  fontWeight: FontWeight.bold,
                                  color: AppColors.forest900,
                                ),
                              )
                            else
                              TextButton(
                                onPressed: _isResending ? null : _handleResend,
                                style: TextButton.styleFrom(
                                  padding: EdgeInsets.zero,
                                  minimumSize: Size.zero,
                                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                                ),
                                child: _isResending
                                    ? const SizedBox(
                                        width: 14,
                                        height: 14,
                                        child: CircularProgressIndicator(strokeWidth: 2),
                                      )
                                    : const Text(
                                        'Resend Code',
                                        style: TextStyle(
                                          fontSize: 13,
                                          fontWeight: FontWeight.bold,
                                          color: AppColors.forest900,
                                          decoration: TextDecoration.underline,
                                        ),
                                      ),
                              ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 20),

                  // Back to edit email
                  TextButton.icon(
                    onPressed: () => Navigator.pop(context),
                    icon: const Icon(Icons.arrow_back_rounded, size: 16, color: AppColors.slate600),
                    label: const Text(
                      'Entered the wrong email? Go back',
                      style: TextStyle(fontSize: 13, color: AppColors.slate600),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
